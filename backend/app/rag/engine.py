import os
import json
import pickle
import asyncio
import numpy as np
import torch
from typing import List, Dict, Optional
from pathlib import Path

# 1. Vector DB & Embeddings
import chromadb
from chromadb.utils import embedding_functions

# 2. NLP & Search
from kiwipiepy import Kiwi
from rank_bm25 import BM25Okapi

# 3. Reranking
from sentence_transformers import CrossEncoder

# Config & Logger
from app.core.config import settings
from app.core.logger import logger


def _download_from_huggingface(repo_id: str, vectordb_dir: Path, use_raw_files: bool = True) -> bool:
    """
    HuggingFace Hub에서 벡터 DB 데이터 다운로드
    HF Spaces 배포 시 자동으로 호출됨

    Args:
        repo_id: HuggingFace 레포지토리 ID
        vectordb_dir: 벡터 DB 저장 경로
        use_raw_files: True면 ChromaDB 파일 직접 다운로드, False면 Dataset 방식
    """
    from huggingface_hub import hf_hub_download, list_repo_files

    logger.info(f"📥 HuggingFace에서 데이터 다운로드 중: {repo_id}")

    try:
        # 디렉토리 생성
        vectordb_dir.mkdir(parents=True, exist_ok=True)
        chroma_dir = vectordb_dir / "chroma_db"
        chroma_dir.mkdir(parents=True, exist_ok=True)

        if use_raw_files:
            # =====================================================
            # 방식 1: ChromaDB 파일 직접 다운로드 (권장)
            # =====================================================
            logger.info("   📦 ChromaDB 파일 직접 다운로드 방식 사용")

            # 레포지토리의 모든 파일 목록 가져오기
            try:
                files = list_repo_files(repo_id, repo_type="dataset")
            except Exception as e:
                logger.error(f"   파일 목록 조회 실패: {e}")
                files = []

            # 다운로드할 파일 패턴
            # HuggingFace 데이터셋의 실제 폴더명: "chroma/" (코드에서는 "chroma_db/"로 저장)
            for file_path in files:
                try:
                    # chroma 또는 chroma_db 폴더 내 파일
                    if file_path.startswith("chroma/") or file_path.startswith("chroma_db/"):
                        # 다운로드 후 chroma_db 폴더로 저장
                        local_path = hf_hub_download(
                            repo_id=repo_id,
                            filename=file_path,
                            repo_type="dataset",
                            local_dir=vectordb_dir,
                        )
                        logger.info(f"   ✅ {file_path} 다운로드 완료")

                    # 루트 레벨 파일 (parent_store.json, bm25_index.pkl)
                    elif file_path in ["parent_store.json", "bm25_index.pkl"]:
                        local_path = hf_hub_download(
                            repo_id=repo_id,
                            filename=file_path,
                            repo_type="dataset",
                            local_dir=vectordb_dir,
                        )
                        logger.info(f"   ✅ {file_path} 다운로드 완료")

                except Exception as e:
                    logger.warning(f"   ⚠️ {file_path} 다운로드 실패: {e}")

            # 다운로드 확인 - chroma 또는 chroma_db 폴더 확인
            chroma_sqlite_path = None
            for folder_name in ["chroma_db", "chroma"]:
                potential_path = vectordb_dir / folder_name / "chroma.sqlite3"
                if potential_path.exists():
                    chroma_sqlite_path = potential_path
                    # chroma 폴더인 경우 chroma_db로 심볼릭 링크 또는 경로 업데이트
                    if folder_name == "chroma":
                        chroma_dir = vectordb_dir / "chroma"
                    break

            if chroma_sqlite_path:
                logger.info(f"   ✅ ChromaDB 파일 다운로드 완료: {chroma_sqlite_path}")
                return True
            else:
                logger.warning("   ⚠️ ChromaDB 파일을 찾을 수 없습니다. Dataset 방식으로 전환...")
                use_raw_files = False

        if not use_raw_files:
            # =====================================================
            # 방식 2: Dataset(parquet) 방식으로 다운로드 후 복원
            # =====================================================
            from datasets import load_dataset

            logger.info("   📊 Dataset 방식으로 다운로드 및 복원")

            # 보조 파일 다운로드
            for filename in ["parent_store.json", "bm25_index.pkl"]:
                try:
                    hf_hub_download(
                        repo_id=repo_id,
                        filename=filename,
                        repo_type="dataset",
                        local_dir=vectordb_dir,
                        local_dir_use_symlinks=False
                    )
                    logger.info(f"   ✅ {filename} 다운로드 완료")
                except Exception as e:
                    logger.warning(f"   ⚠️ {filename} 다운로드 실패: {e}")

            # Dataset 로드
            logger.info("   📊 벡터 데이터셋 로드 중...")
            dataset = load_dataset(repo_id, split="train")
            logger.info(f"   ✅ {len(dataset)}개 문서 로드 완료")

            # ChromaDB 클라이언트 생성
            client = chromadb.PersistentClient(path=str(chroma_dir))

            # 기존 컬렉션 삭제
            try:
                client.delete_collection(name="rag_collection")
            except:
                pass

            # 임베딩 함수 설정
            device = "cuda" if torch.cuda.is_available() else "cpu"
            embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="BAAI/bge-large-en-v1.5",
                device=device,
                normalize_embeddings=True
            )

            # 새 컬렉션 생성
            collection = client.create_collection(
                name="rag_collection",
                embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )

            # 데이터 삽입 (배치 처리)
            batch_size = 100
            total = len(dataset)

            for i in range(0, total, batch_size):
                batch = dataset[i:i + batch_size]

                collection.add(
                    ids=batch["id"],
                    documents=batch["document"],
                    embeddings=batch["embedding"],
                    metadatas=[json.loads(m) for m in batch["metadata"]]
                )

                progress = min(i + batch_size, total)
                if progress % 500 == 0 or progress == total:
                    logger.info(f"   📥 ChromaDB 복원 진행률: {progress}/{total}")

            logger.info(f"   ✅ ChromaDB 복원 완료: {collection.count()}개 문서")

        return True

    except Exception as e:
        logger.error(f"❌ HuggingFace 데이터 다운로드 실패: {e}")
        return False

class WelfareRAG:
    """
    [Local RAG Engine - Production Ready]
    - Hybrid Search (Vector + BM25)
    - Reranking (Cross-Encoder)
    - Parent Document Retrieval
    - Non-blocking Async Support
    """

    def __init__(self):
        # ---------------------------------------------------------
        # 1. 경로 및 기본 설정
        # ---------------------------------------------------------
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        vectordb_dir = self.base_dir / "vectordb"

        # ChromaDB 경로 - chroma_db 또는 chroma 폴더 자동 감지
        self.persist_directory = vectordb_dir / "chroma_db"
        if not self.persist_directory.exists():
            # HuggingFace 데이터셋은 "chroma" 폴더 사용
            alt_path = vectordb_dir / "chroma"
            if alt_path.exists():
                self.persist_directory = alt_path

        self.bm25_path = vectordb_dir / "bm25_index.pkl"
        self.parent_store_path = vectordb_dir / "parent_store.json"

        # 실제 데이터가 있는 컬렉션 이름
        self.default_collection_name = "rag_collection"

        logger.info("="*50)
        logger.info(f"🚀 RAG 엔진 초기화 시작")

        # ---------------------------------------------------------
        # 1.5. HuggingFace에서 데이터 다운로드 (필요시)
        # ---------------------------------------------------------
        def find_chroma_db():
            """chroma.sqlite3 파일이 있는 경로 찾기"""
            for folder_name in ["chroma_db", "chroma"]:
                potential_path = vectordb_dir / folder_name
                if (potential_path / "chroma.sqlite3").exists():
                    return potential_path
            return None

        chroma_path = find_chroma_db()

        if not chroma_path:
            # 로컬에 DB가 없으면 HuggingFace에서 다운로드 시도
            if settings.USE_HF_DATASET and settings.HF_DATASET_REPO_ID:
                logger.info("📦 로컬 DB가 없습니다. HuggingFace에서 다운로드를 시도합니다...")
                success = _download_from_huggingface(
                    repo_id=settings.HF_DATASET_REPO_ID,
                    vectordb_dir=vectordb_dir,
                    use_raw_files=settings.HF_USE_RAW_FILES
                )
                if not success:
                    raise RuntimeError("HuggingFace에서 데이터 다운로드 실패!")

                # 다운로드 후 경로 재확인
                chroma_path = find_chroma_db()
            else:
                logger.critical(f"🚨 DB 파일이 없습니다! 경로를 확인하세요: {vectordb_dir}")

        # 찾은 경로로 업데이트
        if chroma_path:
            self.persist_directory = chroma_path
            logger.info(f"✅ ChromaDB 경로: {self.persist_directory}")

        # ---------------------------------------------------------
        # 2. ChromaDB 연결 및 컬렉션 로드
        # ---------------------------------------------------------
        if not (self.persist_directory / "chroma.sqlite3").exists():
            raise RuntimeError(f"DB 파일이 없습니다: {self.persist_directory}")
        
        self.chroma_client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # GPU 확인
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 임베딩 함수 설정 (DB 생성 시 사용한 모델과 동일해야 함)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-large-en-v1.5",
            device=device,
            normalize_embeddings=True
        )

        # 컬렉션 연결 (안전장치 포함)
        try:
            existing_collections = [c.name for c in self.chroma_client.list_collections()]
            target_name = self.default_collection_name

            if target_name not in existing_collections and len(existing_collections) > 0:
                target_name = existing_collections[0]
                logger.warning(f"⚠️ 설정된 '{self.default_collection_name}' 컬렉션이 없어 '{target_name}'(으)로 자동 연결합니다.")
            
            self.collection = self.chroma_client.get_collection(
                name=target_name,
                embedding_function=self.embedding_fn
            )
            
            doc_count = self.collection.count()
            logger.info(f"✅ ChromaDB 로드 성공: [{target_name}] (문서 수: {doc_count}개)")

        except Exception as e:
            logger.error(f"❌ 컬렉션 로드 중 치명적 오류: {e}")
            raise e

        # ---------------------------------------------------------
        # 3. BM25 인덱스 로드 (Dict -> Object 변환 로직 추가)
        # ---------------------------------------------------------
        self.kiwi = Kiwi()
        self.bm25 = None
        
        if self.bm25_path.exists():
            try:
                with open(self.bm25_path, "rb") as f:
                    loaded_data = pickle.load(f)
                
                # ★ [핵심 수정] 로드된 데이터가 dict인 경우 객체로 변환
                if isinstance(loaded_data, dict):
                    logger.info("⚠️ BM25 파일이 딕셔너리 형식입니다. 객체로 변환합니다.")
                    # 1. 빈 껍데기 BM25 객체 생성 (더미 데이터로 초기화)
                    self.bm25 = BM25Okapi(["a"]) 
                    # 2. 딕셔너리 내용을 객체 속성으로 덮어쓰기
                    self.bm25.__dict__.update(loaded_data)
                else:
                    self.bm25 = loaded_data

                logger.info("✅ BM25 인덱스 로드 완료")
                
            except Exception as e:
                logger.error(f"❌ BM25 로드 실패: {e}")
        else:
            logger.warning(f"⚠️ BM25 파일이 없습니다: {self.bm25_path}")

        # ---------------------------------------------------------
        # 4. Parent Store 로드
        # ---------------------------------------------------------
        self.parent_store = {}
        if self.parent_store_path.exists():
            try:
                with open(self.parent_store_path, "r", encoding="utf-8") as f:
                    self.parent_store = json.load(f)
                logger.info(f"✅ Parent Store 로드 완료 ({len(self.parent_store)}개 항목)")
            except Exception as e:
                logger.error(f"❌ Parent Store 로드 실패: {e}")
        else:
            logger.warning("⚠️ Parent Store 파일이 없습니다.")

        # ---------------------------------------------------------
        # 5. Reranker 로드
        # ---------------------------------------------------------
        try:
            logger.info("🔧 Reranker 모델 로드 중...")
            self.reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device=device)
            logger.info("✅ Reranker 로드 완료")
        except Exception as e:
            logger.warning(f"Reranker 로드 실패: {e}")
            self.reranker = None
            
        # ---------------------------------------------------------
        # 6. BM25용 전체 문서 ID 캐시
        # ---------------------------------------------------------
        try:
            self._all_doc_ids = self.collection.get()['ids']
            logger.info(f"✅ 문서 ID 캐시 완료 ({len(self._all_doc_ids)}개)")
        except Exception as e:
            logger.error(f"❌ 문서 ID 캐시 실패: {e}")
            self._all_doc_ids = []

        logger.info("="*50)

    def _batch_get(self, ids: List[str], batch_size: int = 500) -> Dict:
        """ChromaDB get()을 배치로 나눠서 SQL 변수 제한 회피"""
        all_ids = []
        all_documents = []
        all_metadatas = []

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            resp = self.collection.get(ids=batch_ids)
            all_ids.extend(resp['ids'])
            all_documents.extend(resp['documents'])
            all_metadatas.extend(resp['metadatas'])

        return {
            'ids': all_ids,
            'documents': all_documents,
            'metadatas': all_metadatas
        }

    def _tokenize(self, text: str) -> List[str]:
        """BM25 검색용 토크나이저"""
        return [token.form for token in self.kiwi.tokenize(text) if token.tag.startswith('N')]

    async def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """[Async Wrapper]"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._search_sync, query, top_k)

    def _search_sync(self, query: str, top_k: int = 3) -> List[Dict]:
        """[Synchronous Search Logic]"""
        
        if self.collection.count() == 0:
            return []

        candidate_k = top_k * 3 
        
        # 1. Vector Search
        vector_results = self.collection.query(
            query_texts=[query], 
            n_results=candidate_k
        )
        
        vector_scores = {}
        if vector_results['ids']:
            ids = vector_results['ids'][0]
            dists = vector_results['distances'][0]
            for i, doc_id in enumerate(ids):
                vector_scores[doc_id] = 1 - dists[i]

        # 2. BM25 Search
        bm25_scores = {}
        if self.bm25:
            try:
                tokens = self._tokenize(query)
                # ★ 여기서 get_scores가 정상 작동해야 함
                scores = self.bm25.get_scores(tokens)
                top_indices = np.argsort(scores)[::-1][:candidate_k]
                
                if len(top_indices) > 0:
                    max_score = scores[top_indices[0]]
                    if max_score <= 0: max_score = 1.0
                    
                    for idx in top_indices:
                        if idx < len(self._all_doc_ids):
                            doc_id = self._all_doc_ids[idx]
                            bm25_scores[doc_id] = scores[idx] / max_score
            except Exception as e:
                logger.error(f"BM25 검색 중 오류: {e}")

        # 3. Ensemble
        ALPHA = 0.7
        merged_candidates = {}
        all_candidate_ids = set(vector_scores.keys()) | set(bm25_scores.keys())
        
        for doc_id in all_candidate_ids:
            v_score = vector_scores.get(doc_id, 0.0)
            b_score = bm25_scores.get(doc_id, 0.0)
            final_score = (v_score * ALPHA) + (b_score * (1 - ALPHA))
            
            merged_candidates[doc_id] = {
                "id": doc_id,
                "score": final_score
            }

        sorted_candidates = sorted(merged_candidates.values(), key=lambda x: x['score'], reverse=True)[:candidate_k]

        # 4. Fetch Content
        candidate_ids = [item['id'] for item in sorted_candidates]
        if not candidate_ids:
            return []

        docs_resp = self._batch_get(candidate_ids)
        
        id_to_text = {}
        id_to_meta = {}
        for i, did in enumerate(docs_resp['ids']):
            id_to_text[did] = docs_resp['documents'][i]
            id_to_meta[did] = docs_resp['metadatas'][i]

        final_candidates = []
        for item in sorted_candidates:
            doc_id = item['id']
            if doc_id in id_to_text:
                item['text'] = id_to_text[doc_id]
                item['metadata'] = id_to_meta[doc_id]
                final_candidates.append(item)

        # 5. Reranking
        if self.reranker and final_candidates:
            pairs = [[query, item['text']] for item in final_candidates]
            try:
                rerank_scores = self.reranker.predict(pairs)
                for i, item in enumerate(final_candidates):
                    item['rerank_score'] = float(rerank_scores[i])
                final_candidates.sort(key=lambda x: x['rerank_score'], reverse=True)
            except Exception as e:
                logger.error(f"Reranking Error: {e}")

        # 6. Parent Document Retrieval
        results = []
        for item in final_candidates[:top_k]:
            rerank_score = item.get('rerank_score', item.get('score', 0))
            if 'rerank_score' in item and rerank_score < 1.0:
                logger.info(f"RAG Filter: Rerank score ({rerank_score:.2f}) is below threshold, skipping irrelevant document.")
                continue
                
            metadata = item['metadata']
            doc_id = item['id']
            parent_id = metadata.get('parent_id')
            
            final_content = item['text']
            
            if parent_id and str(parent_id) in self.parent_store:
                final_content = self.parent_store[str(parent_id)].get('page_content', item['text'])
            elif 'parent_content' in metadata:
                final_content = metadata['parent_content']

            results.append({
                "content": final_content,
                "score": item.get('rerank_score', item['score']),
                "metadata": metadata
            })
            
        return results

rag_engine = WelfareRAG()