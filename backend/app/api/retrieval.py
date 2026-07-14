from fastapi import APIRouter, Depends, HTTPException, status
from app.core.qdrant import get_qdrant_client
from app.core.security import get_current_user
from app.repositories.vector_repository import VectorRepository
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.schemas.retrieval import RetrievalSearchRequest, RetrievalSearchResponse

router = APIRouter(prefix="/retrieval", tags=["retrieval"])

def get_retrieval_service() -> RetrievalService:
    client = get_qdrant_client()
    v_repo = VectorRepository(client)
    embed = EmbeddingService()
    return RetrievalService(v_repo, embed)

@router.post("/search", response_model=RetrievalSearchResponse)
async def search_retrieval(
    request_in: RetrievalSearchRequest,
    retrieval_svc: RetrievalService = Depends(get_retrieval_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves the top ranked document chunks for a given query, scoped by project.
    Executes intent classification, hybrid retrieval, and cross-encoder reranking.
    """
    try:
        results = retrieval_svc.retrieve(
            query=request_in.query,
            project_id=request_in.project_id,
            filters=request_in.filters,
            enable_hybrid=request_in.enable_hybrid,
            alpha=request_in.alpha,
            max_tokens=request_in.max_tokens
        )
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval search execution failed: {e}"
        )
