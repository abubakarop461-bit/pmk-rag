import time
from typing import List, Dict, Any
from loguru import logger
from sentence_transformers import CrossEncoder

_reranker_model = None

def get_reranker() -> CrossEncoder:
    """Singleton getter for the reranker model."""
    global _reranker_model
    if _reranker_model is None:
        logger.info("RerankerService loading BAAI/bge-reranker-base model on CPU...")
        _reranker_model = CrossEncoder("BAAI/bge-reranker-base", device="cpu")
    return _reranker_model

class RerankerService:
    def rerank(self, query: str, candidates: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Calculates Cross-Encoder similarity scores for candidate pairs.
        """
        if not candidates:
            return []
            
        logger.info(f"RerankerService evaluating {len(candidates)} candidate text pairs...")
        model = get_reranker()
        
        pairs = [[query, cand["text"]] for cand in candidates]
        scores = model.predict(pairs)
        
        for cand, score in zip(candidates, scores):
            cand["rerank_score"] = float(score)
            
        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        logger.info("Reranking completed successfully.")
        return candidates[:limit]
