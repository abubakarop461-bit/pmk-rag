import os
import shutil
from typing import Dict, Any, BinaryIO, Optional
from fastapi import BackgroundTasks
from loguru import logger

from app.repositories.document_repository import DocumentRepository
from app.storage.storage_service import LocalStorageService
from app.services.audit_service import AuditService
from app.background.local_queue import LocalBackgroundTasksQueue
from app.background.ingestion_worker import process_document_task

class IngestionService:
    def __init__(
        self, 
        document_repository: DocumentRepository, 
        storage_service: LocalStorageService, 
        audit_service: AuditService
    ):
        self.doc_repo = document_repository
        self.storage = storage_service
        self.audit = audit_service

    def save_and_register_document(
        self, 
        project_id: str, 
        document_name: str, 
        document_type: str, 
        revision_number: str, 
        file_stream: BinaryIO, 
        mime_type: str, 
        user_id: str,
        background_tasks: BackgroundTasks,
        ai_classified_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Saves the file to local storage, inserts SQL records in 'pending' status,
        and enqueues the heavy parsing/validation task in the background queue.
        Returns immediately without blocking.
        """
        logger.info(f"IngestionService queuing document: '{document_name}' Rev '{revision_number}'")
        
        # 1. Create logical document row if missing
        logical_doc = self.doc_repo.get_document_by_name(project_id, document_name)
        is_new_doc = logical_doc is None
        
        if not is_new_doc:
            doc_id = logical_doc["id"]
            # Fast check if revision identifier already exists in SQL database
            existing_rev = self.doc_repo.get_revision_by_number(doc_id, revision_number)
            if existing_rev:
                raise ValueError(f"Revision '{revision_number}' already exists for document '{document_name}'.")
        else:
            # Create a logical document placeholder
            logical_doc = self.doc_repo.create_document(
                project_id=project_id, 
                document_name=document_name, 
                document_type=document_type,
                ai_classified_type=ai_classified_type
            )
            doc_id = logical_doc["id"]
            
        # 2. Save physical file stream to local storage folder immediately
        ext = os.path.splitext(document_name)[1]
        stored_filename = f"{doc_id}_{revision_number}{ext}"
        
        project_storage_dir = os.path.join(self.storage.upload_dir, "projects", project_id)
        os.makedirs(project_storage_dir, exist_ok=True)
        target_path = os.path.join(project_storage_dir, stored_filename)
        
        import time
        import hashlib

        upload_start = time.time()
        try:
            with open(target_path, "wb") as f_out:
                shutil.copyfileobj(file_stream, f_out)
            logger.info(f"Buffered physical file to: {target_path}")
        except Exception as e:
            if is_new_doc:
                self.doc_repo.delete_document(doc_id)
            raise RuntimeError(f"Failed to buffer uploaded file locally: {e}")
        
        upload_ms = int((time.time() - upload_start) * 1000)

        # Get file size to insert initial metadata
        file_size = os.path.getsize(target_path)
        
        # Pre-compute SHA-256 checksum of the saved file
        hasher = hashlib.sha256()
        with open(target_path, "rb") as f_hash:
            for block in iter(lambda: f_hash.read(65536), b""):
                hasher.update(block)
        checksum = hasher.hexdigest()

        # Check system-wide duplicates
        existing_ready_rev = self.doc_repo.get_any_ready_revision_by_checksum(checksum)
        if existing_ready_rev:
            existing_doc_res = self.doc_repo.client.table("documents").select("project_id").eq("id", existing_ready_rev["document_id"]).execute()
            if existing_doc_res.data and str(existing_doc_res.data[0]["project_id"]) == str(project_id):
                # Duplicate upload in the same project: clean up saved physical file and logical document record if new
                if os.path.exists(target_path):
                    os.remove(target_path)
                if is_new_doc:
                    self.doc_repo.delete_document(doc_id)
                raise ValueError("Document already indexed.")
        
        # 3. Create document revision record in SQL with status 'pending'
        revision_data = {
            "document_id": doc_id,
            "revision_number": revision_number,
            "storage_path": target_path,
            "mime_type": mime_type,
            "file_size": file_size,
            "checksum": checksum,
            "processing_status": "pending",
            "created_by": user_id
        }
        
        try:
            created_rev = self.doc_repo.create_revision(revision_data)
        except Exception as sql_err:
            if os.path.exists(target_path):
                os.remove(target_path)
            if is_new_doc:
                self.doc_repo.delete_document(doc_id)
            raise sql_err
            
        # 4. Log initial upload event to audit trail
        action_log = "version_created" if not is_new_doc else "document_uploaded"
        try:
            self.audit.log_event(
                user_id=user_id,
                action=action_log,
                details={
                    "project_id": project_id,
                    "document_id": doc_id,
                    "document_name": document_name,
                    "revision": revision_number,
                    "file_size": file_size,
                    "status": "pending"
                }
            )
        except Exception as log_err:
            logger.warning(f"Failed to write upload audit log: {log_err}")
            
        # 5. Queue validation, checksumming, and parsing worker in the background
        queue = LocalBackgroundTasksQueue(background_tasks)
        job_id = queue.enqueue(
            process_document_task,
            project_id=project_id,
            document_id=doc_id,
            revision_id=created_rev["id"],
            file_path=target_path,
            document_name=document_name,
            document_type=document_type,
            revision_number=revision_number,
            mime_type=mime_type,
            user_id=user_id,
            upload_ms=upload_ms
        )
        
        logger.info(f"Registered background worker job ID: {job_id} for file validation and parsing.")
        
        return {
            "document": logical_doc,
            "revision": created_rev,
            "job_id": job_id
        }

