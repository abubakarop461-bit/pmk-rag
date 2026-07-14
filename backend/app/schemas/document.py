from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class DocumentBase(BaseModel):
    document_name: str
    document_type: str
    ai_classified_type: Optional[str] = None

class RevisionOut(BaseModel):
    id: str
    document_id: str
    revision_number: str
    storage_path: str
    mime_type: str
    file_size: int
    checksum: str
    processing_status: str
    error_message: Optional[str] = None
    indexed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentOut(DocumentBase):
    id: str
    project_id: str
    created_at: datetime
    latest_revision: Optional[RevisionOut] = None

    class Config:
        from_attributes = True
