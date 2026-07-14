from typing import List, Dict, Any
from loguru import logger

from app.repositories.vector_repository import VectorRepository
from app.services.embedding_service import EmbeddingService

class HybridSearchService:
    def __init__(self, vector_repository: VectorRepository, embedding_service: EmbeddingService):
        self.vector_repo = vector_repository
        self.embed_svc = embedding_service

    def search(
        self, 
        clean_query: str, 
        filters: Dict[str, Any], 
        enable_hybrid: bool = True, 
        alpha: float = 0.5,
        collection_name: str = "rag_documents"
    ) -> List[Dict[str, Any]]:
        """
        Queries Qdrant using vector embeddings and full-text indexes, merging the results.
        """
        logger.info(f"HybridSearchService searching collection: '{collection_name}' (Hybrid={enable_hybrid})")
        
        # 1. Vector Similarity Search
        query_vector = self.embed_svc.embed_text(clean_query)
        vector_results = self.vector_repo.search_vectors(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=20,
            payload_filter=filters
        )
        
        # 2. Full-Text Index Matching
        keyword_results = []
        if enable_hybrid:
            keyword_results = self.vector_repo.search_text(
                collection_name=collection_name,
                query=clean_query,
                limit=20,
                payload_filter=filters
            )
            
        # 3. Merge & Deduplicate
        merged = {}
        for point in vector_results:
            merged[point.id] = {
                "id": point.id,
                "text": point.payload.get("text", ""),
                "page_number": point.payload.get("page_number", 1),
                "chunk_index": point.payload.get("chunk_index", 1),
                "document_id": point.payload.get("document_id", ""),
                "revision_id": point.payload.get("revision_id", ""),
                "project_id": point.payload.get("project_id", ""),
                "document_type": point.payload.get("document_type", ""),
                "filename": point.payload.get("metadata", {}).get("filename", "N/A"),
                "vector_score": point.score,
                "keyword_score": 0.0
            }
            
        for point in keyword_results:
            pid = point.id
            if pid in merged:
                merged[pid]["keyword_score"] = 1.0  # matched keywords
            else:
                merged[pid] = {
                    "id": pid,
                    "text": point.payload.get("text", ""),
                    "page_number": point.payload.get("page_number", 1),
                    "chunk_index": point.payload.get("chunk_index", 1),
                    "document_id": point.payload.get("document_id", ""),
                    "revision_id": point.payload.get("revision_id", ""),
                    "project_id": point.payload.get("project_id", ""),
                    "document_type": point.payload.get("document_type", ""),
                    "filename": point.payload.get("metadata", {}).get("filename", "N/A"),
                    "vector_score": 0.0,
                    "keyword_score": 1.0
                }
                
        # Calculate hybrid score
        candidates = list(merged.values())
        for cand in candidates:
            cand["hybrid_score"] = alpha * cand["vector_score"] + (1.0 - alpha) * cand["keyword_score"]
            
        candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)
        logger.info(f"HybridSearchService compiled {len(candidates)} unique search candidates.")
        return candidates[:20]
