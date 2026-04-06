"""
MCP 외부 검색 클라이언트.

설명: 정부24, 복지로와 같은 한국의 대표 복지 포털 등을 비동기로 호출, 질의하며
    업데이트 된 복지 프로그램의 정보 구문이나 요건등 제출 가능한 요건/링크를 탐색 추출합니다.
    기존 하이브리드 RAG 엔진 단에서 보조 서포터 역할 레이어로 설계 및 제공 됩니다.
"""

import asyncio
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

import httpx

from app.core.logger import logger


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    """
    설명: 각 정부 포털측에서 단일적으로 하나씩 추출 파싱되어 정제된 검색 결과 아이템 박스.
    필드:
        title           - 포털 결과창 타이틀 텍스트.
        url             - 다이렉트 다큐먼트 페이지 접근 링크 주소.
        snippet         - 프로그램 등에 대한 묘사가 기록되어있는 조각(단락) 문구 데이터.
        source          - 출처 기록 킷값 (e.g. 'gov24', 'bokjiro').
        relevance_score - 결과가 지닌 질의어와의 연관 점수 [0.0, 1.0].
        metadata        - 추가적으로 활용될수도있는 잔여 데이터 박스.
    """

    title: str
    url: str
    snippet: str
    source: str
    relevance_score: float = 0.0
    metadata: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class MCPSearchClient:
    """
    설명: 복지 안내를 돕는 한국형 복지 검색 연동 MCP 전용 기반 클라이언트.
    작동 방식: 비동기(Async) 인터페이스를 바탕으로 복수의 포털에 동시에 검색 쿼리(Query)를 병렬 송신합니다.
        httpx.AsyncClient 등을 구동함으로써 블로킹 없는 연결망 통신을 유지하며 에러가 발생해도 
        프로세스가 중지되거나 정지 오류가 생기지 않도록 모두 내부 핸들링(예외 통과 및 빈 응답 반환)이 철저하게 
        구현되어 있으므로, 검색 에러 시에도 기존 메인 RAG 사이클의 리포트 송신을 해치지 못하게 설정됩니다.
    """

    # ------------------------------------------------------------------
    # Portal registry – add new portals here without touching method code
    # ------------------------------------------------------------------
    PORTALS: Dict[str, Dict[str, str]] = {
        "gov24": {
            "name": "정부24",
            "base_url": "https://www.gov.kr",
            "search_path": "/search?query={query}",
            "doc_url": "https://www.gov.kr/portal/service",
        },
        "bokjiro": {
            "name": "복지로",
            "base_url": "https://www.bokjiro.go.kr",
            "search_path": (
                "/ssis-tbu/TWAT52005M/twataa/wlfareInfo/list.do"
                "?searchTerm={query}"
            ),
            "doc_url": (
                "https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo"
                "/moveTWAT52011M.do"
            ),
        },
        "ehome": {
            "name": "정부24 민원",
            "base_url": "https://www.gov.kr",
            "search_path": "/mw/AA020InfoCapp498702?query={query}",
            "doc_url": "https://www.gov.kr/portal/minwon",
        },
    }

    # Common browser-like headers to reduce request blocking
    _DEFAULT_HEADERS: Dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    _REQUEST_TIMEOUT: float = 10.0   # seconds per request
    _MAX_RETRIES: int = 1            # one retry after initial failure
    _BACKOFF_FACTOR: float = 1.5     # seconds to wait before retry

    def __init__(self) -> None:
        """
        설명: 내부 연결 설정치 값을 포함시켜 MCPSearchClient 베이스를 활성화(Init) 시킵니다.
        작동 방식: 객체 상주(Singleton) 모델을 염두하여 설계되어있어서 이곳 init에선 무겁고 
            부하가 거친 연결 초기 작업이 생략되고 패스 처리 됩니다. 클라이언트 연결체는
            안정적인 httpx 단에서 순람 콜 단위(Call-by-call)로써 컨텍스트에 씌인채로 유지되도록 디자인 됨.
        """
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        portals: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        설명: 주어진 쿼리와 알맞는 관련 복지 자원 정보를 외부 포탈에서 병렬 조회하여 탐색.
        작동 방식:
            1. 정부 포탈 검색에 부합하는 형태로 쿼리 텍스트 전처리(Normalise) 셋업.
            2. 설정 등록되어있는 목표 조회 대상 포탈 검토 확인.
            3. asyncio 비동기 분배를 바탕으로 외부 웹 포탈을 병렬 호출 스캐닝 연쇄 실시 (지연방지).
            4. 모아진 결과치들을 병합, 중복제거, 및 필터 컷팅(Flatteing).
            5. 키워드 오버랩 연산치를 활용하여 내부 로직에 의한 유사 스코어를 매김 (Score).
            6. 점수순대로 최상위 top-k개의 SearchResult 요소만을 리스트업 반환.
        반환값: 점수가 평가되어 나열된 SearchResult 모델들의 리스트 배열.
        예외: 포털 단의 서버 오류나 접속 파손의 예외상태가 발생하더라도 강제로 Raise를 유발시키진 않으며
            (빈 리스트로 전송되며) 백그라운드쪽 로깅 기록 메시지에 기록해 경고등(Warning)을 깜박입니다.
        """
        normalised_query = self._normalise_query(query)
        portal_keys = portals if portals else list(self.PORTALS.keys())

        # Validate supplied portal keys
        valid_keys = [k for k in portal_keys if k in self.PORTALS]
        if not valid_keys:
            logger.warning(
                "MCPSearchClient.search: no valid portal keys provided; "
                "using all portals."
            )
            valid_keys = list(self.PORTALS.keys())

        logger.info(
            f"MCPSearchClient.search: querying portals={valid_keys} "
            f"with query='{normalised_query}'"
        )

        # Fan-out searches in parallel
        tasks = [self._search_portal(pk, normalised_query) for pk in valid_keys]
        portal_results: List[List[SearchResult]] = await asyncio.gather(
            *tasks, return_exceptions=False
        )

        # Flatten
        all_results: List[SearchResult] = []
        for result_list in portal_results:
            all_results.extend(result_list)

        if not all_results:
            logger.warning(
                f"MCPSearchClient.search: all portals returned empty results "
                f"for query='{normalised_query}'"
            )
            return []

        # Score and sort
        scored = self._score_results(all_results, normalised_query)
        scored.sort(key=lambda r: r.relevance_score, reverse=True)

        logger.info(
            f"MCPSearchClient.search: returning {min(top_k, len(scored))} "
            f"results out of {len(scored)} total."
        )
        return scored[:top_k]

    async def search_eligibility(
        self, program_name: str, user_info: Dict
    ) -> Dict:
        """
        설명: 현재 호출 요청받은 복지 정보 내용 대상건에 대한 자격기준 요건을 상세 검색 및 참조 비교.
        작동 방식:
            1. '수급자격' 등의 구체적인 탐색 프롬프트(쿼리스트링)를 추가 가공 연결 병합.
            2. 자가 메서드인 self.search()를 베이스로 풀 스캔.
            3. 반환 도출된 스니펫 단락들에 대해 자격 기준 관련 Regex 키워드들을 재탐색 분류 추출.
                (e.g., 특정 나이대 초과/세 이상, 중위 소득 배율 수치 퍼센트, 장애 등급 계측기준...)
            4. 정형화 및 수집된 어구 단위들의 딕셔너리 재집계.
            5. 결과물 단락에 높은 가중치 점수를 얻은 페이지 주소(Url)를 소스 밸류로서 등록.
        반환값:
            'criteria'     - 대상 자격 제한 조건 추출 결과 구문 문자열.
            'source_url'   - 레퍼런스 페이지 원본 주소지.
        예외: 발견해 탐색 획득해내는데 모두 실패(Failed)한다면 조용히 내부 빈 Dict만 표출해내고 리턴됨.
        """
        eligibility_query = f"{program_name} 신청자격 수급자격 조건"

        logger.info(
            f"MCPSearchClient.search_eligibility: program='{program_name}'"
        )

        results = await self.search(eligibility_query, top_k=5)
        if not results:
            logger.warning(
                f"MCPSearchClient.search_eligibility: no results for "
                f"program='{program_name}'"
            )
            return {}

        # Extract eligibility phrases from snippets using simple keyword patterns
        eligibility_patterns = [
            r"[0-9]+세\s*(?:이상|미만|이하|초과)",       # age conditions
            r"기준\s*중위\s*소득\s*[0-9]+\s*%",           # income threshold
            r"(?:주민등록|거주|거주지)\s*[^\s]{1,20}",     # residency
            r"장애[등급\s]*[1-6]급",                       # disability grade
            r"(?:기초생활|차상위|한부모|다문화)[^\s]{0,15}", # vulnerable groups
            r"(?:무주택|청약|임대)[^\s]{0,15}",             # housing
        ]

        criteria: List[str] = []
        for result in results:
            combined_text = f"{result.title} {result.snippet}"
            for pattern in eligibility_patterns:
                matches = re.findall(pattern, combined_text, re.UNICODE)
                for match in matches:
                    clean = match.strip()
                    if clean and clean not in criteria:
                        criteria.append(clean)

        source_url = results[0].url if results else ""

        return {
            "criteria": criteria,
            "source_url": source_url,
            "last_updated": "N/A",
        }

    async def search_required_documents(self, program_name: str) -> List[Dict]:
        """
        설명: 지정된 복지 서포트 정책 신청을 넣을 때 필요한 서류 문서들을 조회 수집.
        작동 방식:
            1. 다큐먼트에 집중되어진 쿼리를 추가 재조성. ('필요서류', '신청서류').
            2. self.search() 호출에 따른 동시다발 검색 시도.
            3. 파싱 스니펫 단원에 보편적으로 한국에서 사용하는 포맷 규격 형태의 정보명단 파악(Regex).
            4. 서류 이름 단위에서 예상되는 최적 발급부서 파악.
            5. 연동되는 발급 링크 및 안내 문구 접합.
        반환값: List of dicts, 각 객체들은 아래 구조 포함:
            'doc_name'    - 공식 문서명 단어 구조,
            'issuer'      - 추정 문서 발급 주소리 등 (e.g. '주민센터'),
            'online_url'  - 포털 등의 정부 접근 링크 URL주소 경로,
            'description' - 그외 안내 설명 문구(description).
        예외: 어떠한 문서 도큐먼트 단락을 찾아내지 못한채 종료되면, 비어있는 빈 배열 리스트 (Empty) 응답 반환.
        """
        doc_query = f"{program_name} 신청서류 필요서류 구비서류"

        logger.info(
            f"MCPSearchClient.search_required_documents: program='{program_name}'"
        )

        results = await self.search(doc_query, top_k=5)
        if not results:
            logger.warning(
                f"MCPSearchClient.search_required_documents: no results for "
                f"program='{program_name}'"
            )
            return []

        # Document keyword -> (issuer, brief description) mapping
        doc_metadata: Dict[str, Dict[str, str]] = {
            "주민등록등본": {
                "issuer": "주민센터 / 정부24",
                "online_url": "https://www.gov.kr/portal/service/serviceInfo/PTR000051028",
                "description": "주소 및 세대 구성원 확인",
            },
            "주민등록초본": {
                "issuer": "주민센터 / 정부24",
                "online_url": "https://www.gov.kr/portal/service/serviceInfo/PTR000051028",
                "description": "주소 변동 이력 확인",
            },
            "가족관계증명서": {
                "issuer": "주민센터 / 대법원 전자가족관계등록시스템",
                "online_url": "https://efamily.scourt.go.kr",
                "description": "가족 구성 및 관계 증명",
            },
            "건강보험료납부확인서": {
                "issuer": "국민건강보험공단",
                "online_url": "https://www.nhis.or.kr",
                "description": "건강보험 납부 내역 및 소득 수준 확인",
            },
            "소득증빙서류": {
                "issuer": "국세청 / 직장",
                "online_url": "https://www.hometax.go.kr",
                "description": "소득 금액 증명",
            },
            "근로소득원천징수영수증": {
                "issuer": "국세청 홈택스",
                "online_url": "https://www.hometax.go.kr",
                "description": "근로 소득 금액 증명",
            },
            "장애인증명서": {
                "issuer": "주민센터 / 국민연금공단",
                "online_url": "https://www.gov.kr/portal/service",
                "description": "장애 등급 및 유형 증명",
            },
            "통장사본": {
                "issuer": "해당 금융기관",
                "online_url": "",
                "description": "급여 입금 계좌 확인",
            },
            "임대차계약서": {
                "issuer": "해당 계약 당사자",
                "online_url": "",
                "description": "현 거주지 임대 현황 확인",
            },
        }

        found_docs: List[Dict] = []
        seen_names: set = set()

        for result in results:
            combined_text = f"{result.title} {result.snippet}"
            for doc_name, meta in doc_metadata.items():
                if doc_name in combined_text and doc_name not in seen_names:
                    seen_names.add(doc_name)
                    found_docs.append(
                        {
                            "doc_name": doc_name,
                            "issuer": meta["issuer"],
                            "online_url": meta["online_url"],
                            "description": meta["description"],
                        }
                    )

        logger.info(
            f"MCPSearchClient.search_required_documents: found "
            f"{len(found_docs)} documents for program='{program_name}'"
        )
        return found_docs

    async def verify_information(self, claim: str, context: str) -> Dict:
        """
        Description: Attempts to verify a welfare-related claim against live portal
            data, returning a confidence rating and source list.
        How it works:
            1. Combines the claim and context into a focused search query.
            2. Queries portals via self.search().
            3. Counts how many results contain keywords from the original claim.
            4. Derives a confidence score from the ratio of corroborating results.
            5. Returns a structured verification dict.
        Returns: Dict with keys:
            'verified'   - bool, True when confidence >= 0.5,
            'confidence' - float in [0.0, 1.0],
            'sources'    - list of URLs from corroborating results.
        Throws: Returns a low-confidence unverified result on failure; never raises.
        """
        verify_query = f"{claim} {context}"

        logger.info(f"MCPSearchClient.verify_information: claim='{claim[:80]}...'")

        results = await self.search(verify_query, top_k=5)
        if not results:
            logger.warning(
                "MCPSearchClient.verify_information: no results returned, "
                "cannot verify."
            )
            return {"verified": False, "confidence": 0.0, "sources": []}

        # Extract significant tokens from the claim for corroboration check
        claim_keywords = self._extract_keywords(claim)

        corroborating_sources: List[str] = []
        for result in results:
            combined = f"{result.title} {result.snippet}".lower()
            hit_count = sum(1 for kw in claim_keywords if kw.lower() in combined)
            if claim_keywords and hit_count / len(claim_keywords) >= 0.3:
                corroborating_sources.append(result.url)

        confidence = (
            len(corroborating_sources) / len(results) if results else 0.0
        )
        verified = confidence >= 0.5

        logger.info(
            f"MCPSearchClient.verify_information: verified={verified}, "
            f"confidence={confidence:.2f}, sources={len(corroborating_sources)}"
        )
        return {
            "verified": verified,
            "confidence": round(confidence, 4),
            "sources": corroborating_sources,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _search_portal(
        self, portal_key: str, query: str
    ) -> List[SearchResult]:
        """
        Description: Searches a single configured portal and returns parsed results,
            retrying once on transient failure.
        How it works:
            1. Looks up the portal configuration from PORTALS.
            2. Builds the full search URL by URL-encoding the query string.
            3. Creates a short-lived httpx.AsyncClient with browser-like headers
               and a 10-second timeout.
            4. Issues an HTTP GET request.
            5. On HTTP 200, delegates to _parse_html_results() to extract items.
            6. On any exception or non-200 status, waits _BACKOFF_FACTOR seconds
               and retries once.
            7. Returns an empty list if both attempts fail, logging the error.
        Returns: List of SearchResult objects extracted from this portal.
        Throws: Never raises; returns an empty list on failure after retries.
        """
        portal_cfg = self.PORTALS.get(portal_key)
        if not portal_cfg:
            logger.warning(
                f"MCPSearchClient._search_portal: unknown portal key '{portal_key}'"
            )
            return []

        encoded_query = urllib.parse.quote(query)
        search_path = portal_cfg["search_path"].replace("{query}", encoded_query)
        url = portal_cfg["base_url"] + search_path

        logger.info(
            f"MCPSearchClient._search_portal: [{portal_cfg['name']}] GET {url}"
        )

        last_error: Optional[Exception] = None
        for attempt in range(self._MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    headers=self._DEFAULT_HEADERS,
                    timeout=self._REQUEST_TIMEOUT,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(url)

                if response.status_code == 200:
                    results = self._parse_html_results(
                        response.text, portal_key, portal_cfg["base_url"]
                    )
                    logger.info(
                        f"MCPSearchClient._search_portal: [{portal_cfg['name']}] "
                        f"parsed {len(results)} results."
                    )
                    return results
                else:
                    logger.warning(
                        f"MCPSearchClient._search_portal: [{portal_cfg['name']}] "
                        f"HTTP {response.status_code} on attempt {attempt + 1}."
                    )
                    last_error = Exception(
                        f"HTTP {response.status_code}"
                    )

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc
                logger.warning(
                    f"MCPSearchClient._search_portal: [{portal_cfg['name']}] "
                    f"request error on attempt {attempt + 1}: {exc}"
                )

            # Wait before retry (skip after last attempt)
            if attempt < self._MAX_RETRIES:
                backoff = self._BACKOFF_FACTOR * (2 ** attempt)
                logger.debug(
                    f"MCPSearchClient._search_portal: retrying in {backoff}s …"
                )
                await asyncio.sleep(backoff)

        logger.error(
            f"MCPSearchClient._search_portal: [{portal_cfg['name']}] "
            f"all attempts failed. Last error: {last_error}"
        )
        return []

    def _parse_html_results(
        self,
        html: str,
        portal_key: str,
        base_url: str,
    ) -> List[SearchResult]:
        """
        Description: Extracts search result items from a raw HTML string using
            lightweight regex-based parsing (no external HTML parser dependency).
        How it works:
            1. Locates <a> anchor tags that resemble result links using a regex.
            2. Extracts the href attribute and visible link text as the title.
            3. Attempts to find an adjacent text snippet by scanning nearby <p>,
               <span>, or <div> content in a limited window.
            4. Normalises relative URLs against the portal base URL.
            5. Strips HTML tags from all extracted text.
            6. Returns up to 10 SearchResult objects to cap memory usage.
        Returns: List of SearchResult objects (at most 10 items per portal).
        Throws: Never raises; returns an empty list if parsing yields no items.
        """
        results: List[SearchResult] = []

        # Match anchor tags with href containing common result path patterns
        anchor_pattern = re.compile(
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        # Pattern to strip all HTML tags
        tag_strip = re.compile(r"<[^>]+>", re.DOTALL)

        # Split HTML into searchable lines for snippet extraction
        lines = html.splitlines()

        for match in anchor_pattern.finditer(html):
            href = match.group(1).strip()
            raw_title = match.group(2).strip()
            title = tag_strip.sub("", raw_title).strip()

            # Skip navigation, empty, javascript, or anchor-only links
            if (
                not title
                or len(title) < 4
                or href.startswith("#")
                or href.startswith("javascript")
                or len(title) > 200
            ):
                continue

            # Require the title to contain at least one Korean character
            if not re.search(r"[\uAC00-\uD7A3]", title):
                continue

            # Normalise URL
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                full_url = base_url + href
            else:
                full_url = base_url + "/" + href

            # Try to find a nearby snippet by scanning adjacent lines
            snippet = self._extract_nearby_snippet(html, match.start(), tag_strip)

            results.append(
                SearchResult(
                    title=title,
                    url=full_url,
                    snippet=snippet,
                    source=portal_key,
                )
            )

            if len(results) >= 10:
                break

        return results

    def _extract_nearby_snippet(
        self,
        html: str,
        position: int,
        tag_strip: re.Pattern,
    ) -> str:
        """
        Description: Extracts a short text snippet from a region near a matched
            position within the raw HTML, attempting to surface descriptive content.
        How it works:
            1. Slices a 500-character window after the anchor position.
            2. Strips all HTML tags from that window.
            3. Collapses whitespace.
            4. Returns the first 150 characters as the snippet.
        Returns: Snippet string (up to 150 characters), or empty string if none found.
        Throws: Never raises.
        """
        try:
            window = html[position: position + 500]
            plain = tag_strip.sub(" ", window)
            plain = re.sub(r"\s+", " ", plain).strip()
            return plain[:150]
        except Exception:
            return ""

    def _normalise_query(self, query: str) -> str:
        """
        Description: Cleans and prepares a raw query string for welfare-portal search.
        How it works:
            1. Strips leading/trailing whitespace.
            2. Collapses internal whitespace sequences to a single space.
            3. Removes characters that are invalid in URL query parameters.
        Returns: Cleaned query string.
        Throws: Never raises.
        """
        query = query.strip()
        query = re.sub(r"\s+", " ", query)
        # Remove characters that commonly break URL construction
        query = re.sub(r"[<>\"{}|\\^`\[\]]", "", query)
        return query

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Description: Extracts significant Korean and numeric tokens from a text
            string for use in result corroboration scoring.
        How it works:
            1. Tokenises on whitespace.
            2. Keeps tokens that contain Korean characters or numeric sequences of
               length >= 2.
            3. Strips punctuation from token boundaries.
            4. Returns deduplicated token list.
        Returns: List of significant keyword strings.
        Throws: Never raises; returns empty list for empty input.
        """
        tokens = text.split()
        keywords: List[str] = []
        seen: set = set()

        for token in tokens:
            clean = re.sub(r"^[^\w가-힣]+|[^\w가-힣]+$", "", token, flags=re.UNICODE)
            if not clean or clean in seen:
                continue
            has_korean = bool(re.search(r"[\uAC00-\uD7A3]", clean))
            has_number = bool(re.search(r"\d{2,}", clean))
            if (has_korean and len(clean) >= 2) or has_number:
                keywords.append(clean)
                seen.add(clean)

        return keywords

    def _score_results(
        self, results: List[SearchResult], query: str
    ) -> List[SearchResult]:
        """
        키워드 연관도 + 날짜 최신성을 결합하여 점수를 매기고,
        과거 연도 자료는 필터링합니다.
        """
        current_year = date.today().year
        keywords = self._extract_keywords(query)

        scored: List[SearchResult] = []
        for result in results:
            combined = f"{result.title} {result.snippet}"

            # 과거 연도 자료 필터링 (2년 이상 된 자료 제외)
            years = re.findall(r'(20\d{2})년', combined)
            if years:
                max_year = max(int(y) for y in years)
                if max_year < current_year - 1:
                    logger.debug(
                        f"MCPSearchClient._score_results: filtering old result "
                        f"({max_year}년): {result.title[:50]}"
                    )
                    continue
                # 최신 연도 보너스: 올해 → +0.3, 작년 → +0.15
                recency_bonus = 0.3 if max_year >= current_year else 0.15
            else:
                # 연도 없으면 최신으로 간주
                recency_bonus = 0.1

            # 키워드 연관도
            if keywords:
                hits = sum(1 for kw in keywords if kw.lower() in combined.lower())
                keyword_score = hits / len(keywords)
            else:
                keyword_score = 0.0

            result.relevance_score = round(keyword_score + recency_bonus, 4)
            scored.append(result)

        return scored


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_mcp_client_instance: Optional[MCPSearchClient] = None


def get_mcp_client() -> MCPSearchClient:
    """
    Description: Returns the module-level singleton MCPSearchClient instance.
    How it works: Uses a simple global variable guard; creates the instance on
        the first call and returns the cached object on all subsequent calls.
        Thread-safety is not required because the client itself is stateless and
        the Global Interpreter Lock protects the assignment in CPython.
    Returns: MCPSearchClient singleton instance.
    Throws: Never raises.
    """
    global _mcp_client_instance
    if _mcp_client_instance is None:
        logger.info("MCPSearchClient: creating singleton instance.")
        _mcp_client_instance = MCPSearchClient()
    return _mcp_client_instance
