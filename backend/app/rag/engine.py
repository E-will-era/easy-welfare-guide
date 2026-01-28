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
        self.persist_directory = self.base_dir / "vectordb" / "chroma_db"
        
        self.bm25_path = self.base_dir / "vectordb" / "bm25_index.pkl"
        self.parent_store_path = self.base_dir / "vectordb" / "parent_store.json"
        
        # 실제 데이터가 있는 컬렉션 이름
        self.default_collection_name = "rag_collection"

        logger.info("="*50)
        logger.info(f"🚀 RAG 엔진 초기화 시작")
        
        # ---------------------------------------------------------
        # 2. ChromaDB 연결 및 컬렉션 로드
        # ---------------------------------------------------------
        if not (self.persist_directory / "chroma.sqlite3").exists():
            logger.critical(f"🚨 DB 파일이 없습니다! 경로를 확인하세요: {self.persist_directory}")
        
        self.chroma_client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # GPU 확인
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 임베딩 함수 설정 (BGE-M3)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-base-en-v1.5",
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
            
        logger.info("="*50)

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
                    
                    # 안전하게 DB ID 가져오기
                    all_ids = self.collection.get()['ids']
                    
                    for idx in top_indices:
                        if idx < len(all_ids):
                            doc_id = all_ids[idx]
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

        docs_resp = self.collection.get(ids=candidate_ids)
        
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