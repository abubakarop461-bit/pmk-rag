from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class RetrievalSearchRequest(BaseModel):
    query: str
    project_id: str
    filters: Optional[Dict[str, Any]] = None
    enable_hybrid: Optional[bool] = True
    alpha: Optional[float] = 0.5
    max_tokens: Optional[int] = 12000

class ContextBlock(BaseModel):
    text: str
    document_id: str
    project_id: str
    revision_id: str
    filename: str
    document_type: str
    pages: List[int]
    chunk_indexes: List[int]
    vector_score: float
    keyword_score: float
    rerank_score: float
    explain: str

class Citation(BaseModel):
    document_id: str
    filename: str
    pages: List[int]
    document_type: str

class ContextPackage(BaseModel):
    context_blocks: List[ContextBlock]
    confidence_summary: str
    total_estimated_tokens: int
    citations: List[Citation]

class RetrievalTimings(BaseModel):
    preprocessing_ms: float
    vector_search_ms: float
    keyword_search_ms: float
    rerank_ms: float
    context_build_ms: float
    total_ms: float

class RetrievalSearchResponse(BaseModel):
    query: str
    detected_intent: str
    applied_filters: Dict[str, Any]
    context_package: ContextPackage
    timings: RetrievalTimings
