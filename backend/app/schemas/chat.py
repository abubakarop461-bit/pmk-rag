from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class ChatSessionCreateRequest(BaseModel):
    project_id: str
    title: str

class ChatSessionResponse(BaseModel):
    id: str
    project_id: str
    user_id: Optional[str]
    title: str
    created_at: datetime

class ChatQueryRequest(BaseModel):
    query: str
    session_id: str
    project_id: str
    max_tokens: Optional[int] = 12000

class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
