import time
from typing import List, Dict, Any, Optional
from loguru import logger

from app.repositories.vector_repository import VectorRepository
from app.services.embedding_service import EmbeddingService
from app.services.query_preprocessing_service import QueryPreprocessingService
from app.services.query_expansion_service import QueryExpansionService
from app.services.query_intent_service import QueryIntentService
from app.services.metadata_filter_service import MetadataFilterService
from app.services.hybrid_search_service import HybridSearchService
from app.services.reranker_service import RerankerService
from app.services.context_builder_service import ContextBuilderService

class RetrievalService:
    def __init__(self, vector_repository: VectorRepository, embedding_service: EmbeddingService):
        self.preprocessor = QueryPreprocessingService()
        self.expansion = QueryExpansionService()
        self.intent_svc = QueryIntentService()
        self.filter_svc = MetadataFilterService()
        self.hybrid_search = HybridSearchService(vector_repository, embedding_service)
        self.reranker = RerankerService()
        self.context_builder = ContextBuilderService()

    def retrieve(
        self, 
        query: str, 
        project_id: str,
        filters: Optional[Dict[str, Any]] = None,
        enable_hybrid: bool = True,
        alpha: float = 0.5,
        max_tokens: Optional[int] = 12000,
        collection_name: str = "rag_documents"
    ) -> Dict[str, Any]:
        """
        Coordinates the modular query pipeline, executes hybrid searches,
        evaluates cross-encoder rerankers, and formats context structures.
        """
        t_start = time.time()
        
        # 1. Preprocessing
        t_pre_start = time.time()
        cleaned_query = self.preprocessor.preprocess(query)
        t_pre_ms = (time.time() - t_pre_start) * 1000
        
        # 2. Query Expansion
        t_exp_start = time.time()
        expanded_query = self.expansion.expand(cleaned_query)
        t_exp_ms = (time.time() - t_exp_start) * 1000
        
        # 3. Intent Detection
        t_int_start = time.time()
        intent, auto_filters = self.intent_svc.detect_intent(cleaned_query)
        t_int_ms = (time.time() - t_int_start) * 1000
        
        # 4. Filter Generation
        t_flt_start = time.time()
        compiled_filters = self.filter_svc.build_filters(
            project_id=project_id,
            user_filters=filters,
            auto_filters=auto_filters
        )
        t_flt_ms = (time.time() - t_flt_start) * 1000
        
        # 5. Hybrid Search
        t_hyb_start = time.time()
        candidates = self.hybrid_search.search(
            clean_query=expanded_query,
            filters=compiled_filters,
            enable_hybrid=enable_hybrid,
            alpha=alpha,
            collection_name=collection_name
        )
        t_hyb_ms = (time.time() - t_hyb_start) * 1000
        
        # 6. Re-ranking
        t_rnk_start = time.time()
        ranked_chunks = self.reranker.rerank(
            query=cleaned_query,
            candidates=candidates,
            limit=10  # Evaluate top 10 for adjacent chunks merging
        )
        t_rnk_ms = (time.time() - t_rnk_start) * 1000
        
        # 7. Compile explain details
        for chunk in ranked_chunks:
            explain_str = (
                f"Matched intent: '{intent}'. "
                f"Expanded query: '{expanded_query}'. "
                f"Filters: {compiled_filters}. "
                f"Vector score: {chunk['vector_score']:.3f}, "
                f"Keyword match: {chunk['keyword_score']:.1f}, "
                f"Rerank score: {chunk['rerank_score']:.3f}."
            )
            chunk["explain"] = explain_str
            
        # 8. Context Package Formatting
        t_ctx_start = time.time()
        context_package = self.context_builder.build_context(
            ranked_chunks=ranked_chunks,
            max_tokens=max_tokens
        )
        t_ctx_ms = (time.time() - t_ctx_start) * 1000
        
        total_time_ms = (time.time() - t_start) * 1000
        
        return {
            "query": cleaned_query,
            "detected_intent": intent,
            "applied_filters": compiled_filters,
            "context_package": context_package,
            "timings": {
                "preprocessing_ms": round(t_pre_ms + t_exp_ms + t_int_ms + t_flt_ms, 2),
                "vector_search_ms": round(t_hyb_ms, 2),
                "keyword_search_ms": round(t_hyb_ms, 2),
                "rerank_ms": round(t_rnk_ms, 2),
                "context_build_ms": round(t_ctx_ms, 2),
                "total_ms": round(total_time_ms, 2)
            }
        }
