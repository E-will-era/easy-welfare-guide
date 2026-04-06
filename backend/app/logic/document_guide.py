"""
document_guide.py

한국 복지 프로그램 신청을 위한 필수 서류 목록을 생성하는 문서 가이드 엔진입니다.

이 엔진은 다음 세 가지 정보 소스를 우선순위에 따라 결합합니다:
  1. MCP 외부 검색 — 정부 포털의 실시간 서류 요구사항
  2. LLM 분석 — 프로그램 맥락에 따라 생성된 구조화된 가이드
  3. 내장된 COMMON_DOCUMENTS 데이터베이스 — 알려진 한국 정부 포털 URL을 포함한 오프라인 대체 수단

각 서류 항목에는 서류명, 발급 기관, 간단한 설명, 그리고 가능한 경우 온라인 발급 URL이 포함됩니다.
"""

from typing import Dict, List, Optional

from app.agents.llm_handler import get_llm_handler
from app.mcp.search_client import get_mcp_client
from app.core.logger import logger
from app.logic.eligibility import EligibilityEngine


# ---------------------------------------------------------------------------
# YAML 프롬프트 템플릿 경로 상수
# ---------------------------------------------------------------------------

_DOCUMENT_GUIDE_PROMPT = "document_guide.yaml"


# ---------------------------------------------------------------------------
# 내장 한국 서류 참조 데이터베이스
# ---------------------------------------------------------------------------

COMMON_DOCUMENTS: Dict[str, Dict] = {
    "주민등록등본": {
        "issuer": "주민센터, 정부24",
        "online_url": "https://www.gov.kr/mw/AA020InfoCapp498702",
        "description": "가구원 및 주소 확인용",
    },
    "주민등록초본": {
        "issuer": "주민센터, 정부24",
        "online_url": "https://www.gov.kr/mw/AA020InfoCapp498702",
        "description": "주소 변동 이력 확인용",
    },
    "소득금액증명원": {
        "issuer": "국세청 홈택스",
        "online_url": "https://www.hometax.go.kr",
        "description": "소득 확인용",
    },
    "건강보험자격득실확인서": {
        "issuer": "국민건강보험공단",
        "online_url": "https://www.nhis.or.kr",
        "description": "건강보험 자격 확인용",
    },
    "건강보험료납부확인서": {
        "issuer": "국민건강보험공단",
        "online_url": "https://www.nhis.or.kr",
        "description": "소득 수준 간접 확인용",
    },
    "가족관계증명서": {
        "issuer": "대법원 전자가족관계등록시스템",
        "online_url": "https://efamily.scourt.go.kr",
        "description": "가족관계 확인용",
    },
    "장애인증명서": {
        "issuer": "주민센터, 정부24",
        "online_url": "https://www.gov.kr/portal/service",
        "description": "장애 등급 확인용",
    },
    "국가유공자확인서": {
        "issuer": "국가보훈처",
        "online_url": "https://www.mpva.go.kr",
        "description": "유공자 자격 확인용",
    },
    "통장사본": {
        "issuer": "해당 금융기관",
        "online_url": None,
        "description": "급여 입금 계좌 확인용",
    },
    "재직증명서": {
        "issuer": "재직 중인 직장",
        "online_url": None,
        "description": "고용 상태 확인용",
    },
    "사업자등록증": {
        "issuer": "국세청 홈택스",
        "online_url": "https://www.hometax.go.kr",
        "description": "자영업자 확인용",
    },
    "임대차계약서": {
        "issuer": "본인 보관",
        "online_url": None,
        "description": "주거 형태 확인용",
    },
    "재산세과세증명서": {
        "issuer": "주민센터, 정부24",
        "online_url": "https://www.gov.kr",
        "description": "재산 확인용",
    },
    "근로소득원천징수영수증": {
        "issuer": "국세청 홈택스",
        "online_url": "https://www.hometax.go.kr",
        "description": "근로 소득 금액 증명용",
    },
    "장애인복지카드": {
        "issuer": "읍·면·동 주민센터",
        "online_url": None,
        "description": "장애인 등록 및 장애 유형·등급 확인용",
    },
    "기초생활수급자증명서": {
        "issuer": "주민센터, 정부24",
        "online_url": "https://www.gov.kr/portal/service",
        "description": "기초생활수급자 자격 확인용",
    },
    "한부모가족증명서": {
        "issuer": "주민센터, 정부24",
        "online_url": "https://www.gov.kr/portal/service",
        "description": "한부모가족 자격 확인용",
    },
    "의료급여증": {
        "issuer": "읍·면·동 주민센터",
        "online_url": None,
        "description": "의료급여 수급 자격 확인용",
    },
}


# ---------------------------------------------------------------------------
# 메인 엔진
# ---------------------------------------------------------------------------

class DocumentGuideEngine:
    """
    설명: 복지 프로그램 서류 안내를 분석하고 생성하는 엔진입니다.
    작동 방식: 싱글톤 패턴으로 구현되었으며, LLM을 활용하여 프로그램 정보에 따른
        공통 서류와 사용자 세부 정보(소득, 나이 등)를 반영한 맞춤형 서류를 리스트화 합니다.
        대체(Fallback) 체인은 다음과 같습니다:
          1. MCP 검색 + LLM (전체 파이프라인)
          2. LLM 전용 (MCP 실패 시)
          3. 내장 데이터베이스 전용 (MCP 및 LLM 모두 실패 시)
        각 서류 항목에는 이름, 발급처, 설명, 온라인 발급 URL, 필수 여부, 선택적 참고사항이 포함됩니다.
    """

    def __init__(self):
        # 설명: 공유 LLM 핸들러와 MCP 클라이언트 싱글톤으로 엔진을 초기화합니다.
        # 작동 방식: 애플리케이션 전반의 싱글톤을 가져와서 하위 클라이언트를 재초기화하지 않고
        #     모든 엔진 메서드 호출에서 재사용합니다.
        # 반환값: 없음.
        self.llm = get_llm_handler()
        self.mcp_client = get_mcp_client()

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    async def generate_document_guide(
        self,
        program_info: str,
        eligibility_result: Optional[Dict] = None,
    ) -> Dict:
        """
        설명: 주어진 복지 프로그램의 정보 구문록과, 유저 환경변수들(옵션)을 바탕으로 
            제출되어져야 할 필요 서류 문서 리스트들을 생성해냅니다.
        작동 방식: 
            1. MCP 검색 클라이언트를 통하여 필요한 서류 문서를 검색합니다. (실패 시 빈 문자열 처리)
            2. eligibility_result(제공된 경우)를 LLM 프롬프트 컨텍스트를 위해 읽기 쉬운 문자열로 포맷팅합니다.
            3. document_guide.yaml을 사용하여 LLM을 호출하고 json_object 응답을 요청합니다.
            4. LLM 응답 성공 시, _enrich_with_database()를 사용하여 누락된 URL이나 발급처 정보를 보완합니다.
            5. LLM 실패 또는 JSON 파싱 오류 시, _generate_fallback_guide()를 통해 대체 가이드를 생성합니다.
            6. 관찰 가능성을 위해 모든 단계와 오류를 로깅합니다.
        반환값: 'program_name', 'documents', 'application_info', 'tips'등의 리스트 포함 dict 양식.
        예외: 어떠한 런타임 오류나 HTTP 실패가 터져도 로깅 출력만 해줄뿐,
            서비스타임 보장을 위해 fallback(대체용) 데이터만 조용하게 뿜어냅니다.
        """
        logger.info(
            f"DocumentGuideEngine.generate_document_guide: "
            f"program_info length={len(program_info)} chars."
        )

        # Step 1: Search MCP for document requirements (with graceful fallback)
        mcp_search_context = await self._search_documents(program_info)

        # Step 2: Format the eligibility result as a readable context string
        eligibility_context = self._format_eligibility_result(eligibility_result)

        # Step 3: Call the LLM with the document_guide.yaml prompt
        logger.info(
            "DocumentGuideEngine.generate_document_guide: calling LLM for document guide."
        )
        try:
            llm_response = await self.llm.run_prompt_template(
                prompt_file=_DOCUMENT_GUIDE_PROMPT,
                variables={
                    "program_info": program_info,
                    "eligibility_result": eligibility_context,
                    "mcp_search_results": mcp_search_context,
                },
                response_format="json_object",
            )
        except Exception as exc:
            logger.error(
                f"DocumentGuideEngine.generate_document_guide: LLM call failed: {exc}"
            )
            return self._generate_fallback_guide(program_info)

        # Step 4: Handle LLM JSON parse errors
        if not isinstance(llm_response, dict) or "error" in llm_response:
            logger.error(
                "DocumentGuideEngine.generate_document_guide: LLM returned invalid "
                f"response: {str(llm_response)[:200]}"
            )
            return self._generate_fallback_guide(program_info)

        # Step 5: Enrich documents with built-in database info
        documents = llm_response.get("documents", [])
        if documents:
            llm_response["documents"] = self._enrich_with_database(documents)
            llm_response["documents"] = self._deduplicate_documents(
                llm_response["documents"]
            )

        logger.info(
            f"DocumentGuideEngine.generate_document_guide: guide generated with "
            f"{len(llm_response.get('documents', []))} documents."
        )
        return llm_response

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    async def _search_documents(self, program_info: str) -> str:
        """
        설명: 프로그램 관련 필수 서류를 찾기 위해 MCP 포털을 검색합니다.
        작동 방식:
            1. MCP 검색 쿼리로 사용할 프로그램 정보에서 검색용 키워드를 추출합니다.
            2. 하드코딩된 필터 없이 일반 search()를 호출하여 원문 조각(Snippet)을 가져옵니다.
            3. 원문 조각을 사람이 읽을 수 있는 다중 행 문자열로 포맷팅하여 LLM이 스스로 서류를 추출하게 돕습니다.
        반환값: MCP 검색 결과의 포맷팅된 문자열; 실패 시 "검색 결과 없음" 반환.
        """
        program_name = EligibilityEngine._extract_program_name(program_info)
        query = program_name + " 신청서류 구비서류"
        logger.info(
            f"DocumentGuideEngine._search_documents: querying MCP with '{query}'"
        )

        try:
            results = await self.mcp_client.search(query, top_k=4)
        except Exception as exc:
            logger.warning(
                f"DocumentGuideEngine._search_documents: MCP search failed: {exc}"
            )
            return "검색 결과 없음"

        if not results:
            logger.info(
                "DocumentGuideEngine._search_documents: MCP returned no documents."
            )
            return "검색 결과 없음"

        # Format the raw snippets into readable context lines for LLM
        lines = []
        for i, doc in enumerate(results, start=1):
            title = doc.title
            snippet = doc.snippet
            line = f"[{i}] 제목: {title}\n내용: {snippet}\n"
            lines.append(line)

        result = "\n".join(lines)
        logger.info(
            f"DocumentGuideEngine._search_documents: formatted {len(results)} "
            "MCP snippets as context."
        )
        return result

    def _enrich_with_database(self, documents: List[Dict]) -> List[Dict]:
        """
        설명: 누락된 필드에 대해 내장 데이터베이스 정보를 사용하여 LLM이 생성한 서류 목록을 보완합니다.
        작동 방식:
            1. 제공된 리스트의 각 서류 딕셔너리를 반복합니다.
            2. 각 서류에 대해 서류명이 COMMON_DOCUMENTS의 키를 포함하는지 대소문자 구분 없이 부분 일치(퍼지 매칭)를 확인합니다.
            3. 일치하는 항목이 발견되면:
               - online_url이 누락된 경우(None 또는 빈 문자열) 채워 넣습니다.
               - issuer가 누락되거나 비어 있는 경우 채워 넣습니다.
            4. 일치하는 데이터베이스 항목이 없는 서류는 변경되지 않은 상태로 반환됩니다.
            5. 원래 순서를 유지하며 보완된 리스트를 반환합니다.
        반환값: COMMON_DOCUMENTS에서 가능한 경우 누락된 online_url 및 issuer 필드가 채워진 서류 딕셔너리 리스트.
        예외: 서류별 보완 오류는 로깅되고 건너뜁니다.
        """
        enriched = []
        for doc in documents:
            try:
                doc_name = doc.get("doc_name", "")
                matched_key = None

                # Fuzzy match: check if the document name contains any DB key
                # (or any DB key contains the document name)
                for db_key in COMMON_DOCUMENTS:
                    if db_key in doc_name or doc_name in db_key:
                        matched_key = db_key
                        break

                if matched_key:
                    db_entry = COMMON_DOCUMENTS[matched_key]

                    # Fill in issuer only if absent
                    current_issuer = doc.get("issuer", "").strip()
                    if not current_issuer and db_entry.get("issuer"):
                        doc["issuer"] = db_entry["issuer"]
                        logger.debug(
                            f"DocumentGuideEngine._enrich_with_database: "
                            f"filled issuer for '{doc_name}' from DB key '{matched_key}'."
                        )

                enriched.append(doc)

            except Exception as exc:
                logger.warning(
                    f"DocumentGuideEngine._enrich_with_database: "
                    f"error enriching document '{doc.get('doc_name', '?')}': {exc}"
                )
                enriched.append(doc)  # Preserve the original entry even on error

        return enriched

    def _deduplicate_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        설명: 서류 목록에서 사실상 동일하거나 포함 관계에 있는 중복 항목을 제거합니다.
        작동 방식:
            1. 각 서류 쌍을 비교하여 doc_name 간 포함 관계를 확인합니다.
               예: '임신확인서'와 '의료비지원신청 및 임신확인서'가 있으면
               더 구체적인(긴) 명칭만 남깁니다.
            2. 제거 대상으로 표시된 인덱스를 건너뛰고 나머지만 반환합니다.
        반환값: 중복이 제거된 서류 딕셔너리 리스트.
        """
        if len(documents) <= 1:
            return documents

        remove_indices = set()
        names = [doc.get("doc_name", "").strip() for doc in documents]

        for i in range(len(names)):
            if i in remove_indices or not names[i]:
                continue
            for j in range(len(names)):
                if i == j or j in remove_indices or not names[j]:
                    continue
                # names[i]가 names[j]에 포함되면 → i(짧은 쪽) 제거
                if names[i] in names[j] and names[i] != names[j]:
                    remove_indices.add(i)
                    logger.info(
                        f"DocumentGuideEngine._deduplicate_documents: "
                        f"'{names[i]}' is contained in '{names[j]}', removing duplicate."
                    )
                    break

        if remove_indices:
            result = [doc for idx, doc in enumerate(documents) if idx not in remove_indices]
            logger.info(
                f"DocumentGuideEngine._deduplicate_documents: "
                f"removed {len(remove_indices)} duplicate(s), "
                f"{len(result)} documents remaining."
            )
            return result

        return documents

    def _generate_fallback_guide(self, program_info: str) -> Dict:
        """
        설명: MCP 검색과 LLM 파이프라인이 모두 실패할 때 최소한의 대체 서류 가이드를 생성합니다.
        작동 방식:
            1. COMMON_DOCUMENTS에서 일반적으로 요구되는 한국 복지 서류의 핵심 하위 집합을 선택합니다: 주민등록등본, 건강보험료납부확인서, 소득금액증명원, 가족관계증명서, 통장사본.
            2. 모든 항목을 필수(is_required=True)로 표시하고 대체 참고사항을 포함하여 표준 출력 형식으로 서류 목록을 구성합니다.
            3. 복지로 및 보건복지부 콜센터(129)를 가리키는 일반적인 application_info 블록을 구축합니다.
            4. 호출자가 항상 유효한 응답 구조를 받을 수 있도록 전체 대체 딕셔너리를 반환합니다.
        반환값: program_name, documents, application_info, tips 키를 포함하는 딕셔너리. 모든 필드는 전체 가이드 형식과 일치하는 한국어를 사용합니다.
        예외: 예외를 발생시키지 않습니다.
        """
        logger.warning(
            "DocumentGuideEngine._generate_fallback_guide: "
            "generating fallback guide due to upstream failure."
        )

        # Core documents commonly required across most Korean welfare programs
        fallback_keys = [
            "주민등록등본",
            "건강보험료납부확인서",
            "소득금액증명원",
            "가족관계증명서",
            "통장사본",
        ]

        documents = []
        for key in fallback_keys:
            db_entry = COMMON_DOCUMENTS.get(key, {})
            documents.append(
                {
                    "doc_name": key,
                    "issuer": db_entry.get("issuer", "해당 기관"),
                    "description": db_entry.get("description", ""),
                    "online_url": db_entry.get("online_url"),
                    "is_required": True,
                    "notes": "프로그램에 따라 추가 서류가 필요할 수 있습니다. 신청 전 담당 기관에 문의하세요.",
                }
            )

        return {
            "program_name": program_info[:50].strip() if program_info else "해당 복지 프로그램",
            "documents": documents,
            "application_info": {
                "where_to_apply": "읍·면·동 주민센터 또는 해당 복지 기관",
                "online_apply_url": "https://www.bokjiro.go.kr",
                "deadline": None,
                "contact": "보건복지부 콜센터 129",
            },
            "tips": [
                "신청 전 복지로(www.bokjiro.go.kr)에서 해당 프로그램의 상세 서류 목록을 확인하세요.",
                "주민등록등본, 가족관계증명서는 정부24(www.gov.kr)에서 무료로 온라인 발급 가능합니다.",
                "서류는 신청일 기준 30일 이내 발급본을 사용하는 것이 일반적입니다.",
                "보건복지부 콜센터(129)에 전화하면 신청 서류 안내를 받을 수 있습니다.",
            ],
        }

    # ------------------------------------------------------------------
    # Private formatting helpers
    # ------------------------------------------------------------------

    def _format_eligibility_result(self, eligibility_result: Optional[Dict]) -> str:
        """
        Description: Converts an eligibility result dict into a concise Korean string
            for injection into the LLM prompt context.
        How it works:
            1. If eligibility_result is None or empty, returns a placeholder string
               indicating no eligibility information is available.
            2. Extracts the standard eligibility fields (eligible, confidence, reason)
               and formats them as labeled Korean lines.
            3. Converts the boolean eligible field to Korean ("자격 있음" / "자격 없음" /
               "미결정") for readability.
        Returns: Formatted multi-line string describing the eligibility outcome,
            or "자격 확인 결과 없음" when eligibility_result is absent.
        Throws: Never raises.
        """
        if not eligibility_result:
            return "자격 확인 결과 없음"

        lines = []

        eligible = eligibility_result.get("eligible")
        if eligible is True:
            lines.append("- 자격 여부: 자격 있음")
        elif eligible is False:
            lines.append("- 자격 여부: 자격 없음")
        else:
            lines.append("- 자격 여부: 미결정")

        confidence = eligibility_result.get("confidence")
        if confidence is not None:
            lines.append(f"- 신뢰도: {confidence:.0%}")

        reason = eligibility_result.get("reason")
        if reason:
            lines.append(f"- 판단 근거: {reason}")

        return "\n".join(lines) if lines else "자격 확인 결과 없음"


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_document_guide_instance: Optional[DocumentGuideEngine] = None


def get_document_guide_engine() -> DocumentGuideEngine:
    """
    Description: Returns the application-wide singleton DocumentGuideEngine instance.
    How it works: Lazily instantiates DocumentGuideEngine on first call and caches
        it in a module-level variable. Subsequent calls return the cached instance,
        avoiding repeated initialization of the underlying LLM handler and MCP client.
    Returns: The singleton DocumentGuideEngine instance.
    Throws: Never raises.
    """
    global _document_guide_instance
    if _document_guide_instance is None:
        _document_guide_instance = DocumentGuideEngine()
        logger.info("DocumentGuideEngine singleton created.")
    return _document_guide_instance
