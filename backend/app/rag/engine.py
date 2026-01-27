import os
import numpy as np
from typing import List, Dict
from pathlib import Path
import torch  # GPU 사용 가능 여부 확인용

# 1. Vector DB & Embeddings
import chromadb
from chromadb.utils import embedding_functions

# 2. NLP & Search (Kiwi + BM25)
from kiwipiepy import Kiwi
from rank_bm25 import BM25Okapi

# 3. Reranking (Cross-Encoder)
from sentence_transformers import CrossEncoder

# Config & Logger
from app.core.config import settings
from app.core.logger import logger

class WelfareRAG:
    """
    [Local RAG Engine]
    1. 임베딩: Hugging Face (BAAI/bge-m3) - 로컬/무료/고성능
    2. 검색 전략: Ensemble (BM25 30% + Vector 70%)
    3. 보완책: ParentDocument (문맥 보존)
    4. Reranking: Cross-Encoder (BAAI/bge-reranker-v2-m3)
    """

    def __init__(self):
        self.persist_directory = Path("vectordb/chroma_db")
        self.collection_name = "welfare_policies"
        
        # --- [Step 1] ChromaDB & Hugging Face Embedding 설정 ---
        self.chroma_client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # GPU 사용 가능 여부 확인
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🔧 임베딩 모델 실행 디바이스: {device.upper()}")

        try:
            # Azure OpenAI 대신 로컬 BGE-M3 모델 사용
            # 최초 실행 시 모델을 자동으로 다운로드합니다 (~2GB)
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="BAAI/bge-m3",
                device=device,
                normalize_embeddings=True  # Cosine Similarity 성능 향상
            )
            
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("✅ HuggingFace Embedding Model (BAAI/bge-m3) 로드 완료")
            
        except Exception as e:
            logger.error(f"ChromaDB 초기화 실패: {e}")
            raise e

        # --- [Step 2] Kiwi & BM25 초기화 ---
        logger.info("🔧 Kiwi 형태소 분석기 로드 중...")
        self.kiwi = Kiwi()
        self.bm25 = None
        self.doc_ids = []
        
        # 서버 시작 시 기존 데이터로 BM25 인덱스 빌드
        self._initialize_bm25()

        # --- [Step 3] Cross-Encoder (Reranking) ---
        # 임베딩과 같은 계열인 bge-reranker 사용 (최적의 호환성)
        rerank_model_name = "BAAI/bge-reranker-v2-m3"
        try:
            logger.info(f"🔧 Reranker 모델 로드 중 ({rerank_model_name})...")
            self.reranker = CrossEncoder(rerank_model_name, device=device)
        except Exception as e:
            logger.warning(f"Reranker 로드 실패: {e}. Reranking 과정은 생략됩니다.")
            self.reranker = None

    def _tokenize(self, text: str) -> List[str]:
        """Kiwi를 사용한 명사(NN) 위주 토큰화 -> BM25 성능 극대화"""
        return [token.form for token in self.kiwi.tokenize(text) if token.tag.startswith('N')]

    def _initialize_bm25(self):
        """DB에 저장된 Child Chunk들을 가져와 BM25 인덱스 생성"""
        try:
            results = self.collection.get()
            documents = results['documents']
            self.doc_ids = results['ids']
            
            if not documents:
                logger.warning("BM25 인덱스 생성 대기: DB에 데이터가 없습니다.")
                return

            tokenized_corpus = [self._tokenize(doc) for doc in documents]
            self.bm25 = BM25Okapi(tokenized_corpus)
            logger.info(f"✅ BM25 인덱스 생성 완료 ({len(documents)}개 문서)")
            
        except Exception as e:
            logger.error(f"BM25 초기화 중 오류: {e}")

    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        [Hybrid Search + Reranking]
        1. Ensemble (Vector 0.7 + BM25 0.3)
        2. Reranking (Top 10)
        3. ParentDocument Mapping
        """
        candidate_k = 10  # Reranking 후보군
        
        # 1. Vector Search (Chroma - BGE-M3)
        vector_results = self.collection.query(query_texts=[query], n_results=candidate_k)
        
        vector_scores = {}
        if vector_results['ids']:
            ids = vector_results['ids'][0]
            dists = vector_results['distances'][0]
            for i, doc_id in enumerate(ids):
                vector_scores[doc_id] = 1 - dists[i]

        # 2. Keyword Search (BM25 - Kiwi)
        bm25_scores = {}
        if self.bm25:
            tokens = self._tokenize(query)
            scores = self.bm25.get_scores(tokens)
            top_indices = np.argsort(scores)[::-1][:candidate_k]
            
            max_score = scores[top_indices[0]] if len(top_indices) > 0 and scores[top_indices[0]] > 0 else 1.0
            for idx in top_indices:
                doc_id = self.doc_ids[idx]
                bm25_scores[doc_id] = scores[idx] / max_score

        # 3. Ensemble (Weighted Fusion)
        ALPHA = 0.7 # Vector 가중치 (BGE-M3 성능이 좋으므로 높게 유지)
        merged_candidates = {}
        all_ids = set(vector_scores.keys()) | set(bm25_scores.keys())
        
        for doc_id in all_ids:
            v_score = vector_scores.get(doc_id, 0.0)
            b_score = bm25_scores.get(doc_id, 0.0)
            final_score = (v_score * ALPHA) + (b_score * (1 - ALPHA))
            
            merged_candidates[doc_id] = {
                "id": doc_id,
                "score": final_score
            }

        sorted_candidates = sorted(merged_candidates.values(), key=lambda x: x['score'], reverse=True)[:candidate_k]

        # 데이터(Text & Metadata) 조회
        final_candidates = []
        for item in sorted_candidates:
            res = self.collection.get(ids=[item['id']])
            if res['documents']:
                item['text'] = res['documents'][0]
                item['metadata'] = res['metadatas'][0]
                final_candidates.append(item)

        # 4. Reranking (Cross-Encoder)
        if self.reranker and final_candidates:
            pairs = [[query, item['text']] for item in final_candidates]
            rerank_scores = self.reranker.predict(pairs)
            
            for i, item in enumerate(final_candidates):
                item['rerank_score'] = float(rerank_scores[i])
            
            final_candidates.sort(key=lambda x: x['rerank_score'], reverse=True)

        # 5. ParentDocument 전략 적용 & 최종 반환
        results = []
        for item in final_candidates[:top_k]:
            metadata = item['metadata']
            
            # ParentContent가 있으면 그것을, 없으면 검색된 Chunk를 반환
            final_content = metadata.get('parent_content', item['text'])
            
            results.append({
                "content": final_content,
                "score": item.get('rerank_score', item['score']),
                "metadata": metadata
            })
            
        return results

# 싱글톤 인스턴스
rag_engine = WelfareRAG()