import os
import asyncio
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from loguru import logger

from app.core.supabase import get_supabase_client
from app.core.security import get_current_user
from app.repositories.document_repository import DocumentRepository
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService
from app.services.ingestion_service import IngestionService
from app.services.parser_service import ParserService
from app.services.document_classification_service import DocumentClassificationService
from app.storage.storage_service import LocalStorageService
from app.schemas.document import DocumentOut, RevisionOut

class DocumentEventManager:
    def __init__(self):
        # Maps project_id to a set of asyncio.Queue instances
        self.listeners = {}

    def subscribe(self, project_id: str) -> asyncio.Queue:
        if project_id not in self.listeners:
            self.listeners[project_id] = set()
        queue = asyncio.Queue()
        self.listeners[project_id].add(queue)
        return queue

    def unsubscribe(self, project_id: str, queue: asyncio.Queue):
        if project_id in self.listeners:
            self.listeners[project_id].discard(queue)
            if not self.listeners[project_id]:
                del self.listeners[project_id]

    def publish(self, project_id: str, event_data: dict):
        if project_id in self.listeners:
            for queue in self.listeners[project_id]:
                try:
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        loop.call_soon_threadsafe(queue.put_nowait, event_data)
                    except RuntimeError:
                        queue.put_nowait(event_data)
                except Exception as e:
                    logger.warning(f"Failed to publish document event: {e}")

document_event_manager = DocumentEventManager()

router = APIRouter(prefix="/documents", tags=["documents"])

def get_doc_repo() -> DocumentRepository:
    client = get_supabase_client()
    return DocumentRepository(client)

def get_parser_service() -> ParserService:
    return ParserService()

def get_classification_service() -> DocumentClassificationService:
    return DocumentClassificationService()

def get_ingestion_service() -> IngestionService:
    client = get_supabase_client()
    doc_repo = DocumentRepository(client)
    storage = LocalStorageService()
    audit_repo = AuditRepository(client)
    audit = AuditService(audit_repo)
    return IngestionService(doc_repo, storage, audit)

@router.get("/project/{project_id}", response_model=List[DocumentOut])
async def list_documents(
    project_id: str,
    repo: DocumentRepository = Depends(get_doc_repo),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve all logical documents in a project along with their latest revision metadata."""
    try:
        return repo.get_project_documents(project_id)
    except Exception as e:
        logger.error(f"Failed to fetch documents for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch documents: {e}"
        )

@router.post("/classify")
async def classify_document_route(
    file: UploadFile = File(...),
    parser: ParserService = Depends(get_parser_service),
    classifier: DocumentClassificationService = Depends(get_classification_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Synchronously extracts first-page text content from an uploaded document 
    and classifies the document type.
    """
    import tempfile
    import shutil
    filename = file.filename or "unknown_file"
    ext = os.path.splitext(filename)[1]
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name
        
    try:
        # Extract text content from the document (limit to first page if multi-page)
        parsed_docs = parser.parse_file(temp_path)
        first_page_text = parsed_docs[0].page_content if parsed_docs else ""
        
        detected_type, confidence = classifier.classify_document(filename, first_page_text)
        return {
            "detected_document_type": detected_type,
            "confidence_score": confidence
        }
    except Exception as e:
        logger.error(f"Classification failed for {filename}: {e}")
        # Default fallback to other if parsing crashes
        return {
            "detected_document_type": "other",
            "confidence_score": 50
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.post("/project/{project_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: str,
    background_tasks: BackgroundTasks,
    document_type: str = Form(...),
    revision_number: str = Form("A"),
    ai_classified_type: Optional[str] = Form(None),
    file: UploadFile = File(...),
    ingest_svc: IngestionService = Depends(get_ingestion_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Uploads a new file binary to local storage and queues its revision chain validation 
    and parsing in the background. Returns a job ID immediately.
    """
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid file upload: missing filename.")
        
    mime_type = file.content_type or "application/octet-stream"
    
    try:
        result = ingest_svc.save_and_register_document(
            project_id=project_id,
            document_name=filename,
            document_type=document_type,
            revision_number=revision_number,
            file_stream=file.file,
            mime_type=mime_type,
            user_id=current_user["id"],
            background_tasks=background_tasks,
            ai_classified_type=ai_classified_type
        )
        return {
            "status": "success",
            "message": "Document upload accepted and queued for processing.",
            "job_id": result["job_id"],
            "document": result["document"],
            "revision": result["revision"]
        }
    except ValueError as val_err:
        # Caught validation errors (e.g. duplicate revisions or checksum clashes)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as e:
        logger.error(f"Ingestion failed for {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion service failure: {e}"
        )

@router.get("/{document_id}/revisions", response_model=List[RevisionOut])
async def get_document_revisions(
    document_id: str,
    repo: DocumentRepository = Depends(get_doc_repo),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves the complete revision history chain for a document."""
    try:
        return repo.get_document_revisions(document_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch revisions: {e}"
        )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_record(
    document_id: str,
    repo: DocumentRepository = Depends(get_doc_repo),
    current_user: dict = Depends(get_current_user)
):
    """Deletes a document record, cleans up local physical files, and deletes Qdrant vectors."""
    try:
        # Retrieve all revision paths to clean up physical storage files
        revisions = repo.get_document_revisions(document_id)
        
        # SQL deletion
        success = repo.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document record not found.")
            
        # Clean up physical files from disk
        for rev in revisions:
            path = rev.get("storage_path")
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as io_err:
                    logger.warning(f"Failed to clean up physical file at {path}: {io_err}")
                    
        # Clean up Qdrant vectors
        try:
            from app.core.qdrant import get_qdrant_client
            from app.repositories.vector_repository import VectorRepository
            v_repo = VectorRepository(get_qdrant_client())
            v_repo.delete_document_vectors("rag_documents", document_id)
        except Exception as q_err:
            logger.warning(f"Failed to clean up Qdrant vectors: {q_err}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {e}"
        )

@router.get("/project/{project_id}/events")
async def document_events_stream(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    SSE stream endpoint yielding real-time document processing status updates.
    """
    async def event_generator():
        queue = document_event_manager.subscribe(project_id)
        try:
            # Yield initial connect event
            yield f"data: {json.dumps({'event': 'connected'})}\n\n"
            while True:
                event_data = await queue.get()
                yield f"data: {json.dumps(event_data)}\n\n"
        except asyncio.CancelledError:
            logger.info(f"SSE listener disconnected for project {project_id}")
        finally:
            document_event_manager.unsubscribe(project_id, queue)

    return StreamingResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        },
        media_type="text/event-stream"
    )

