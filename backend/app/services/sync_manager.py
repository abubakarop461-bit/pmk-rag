import io
import time
import hashlib
from typing import Dict, Any, List, Optional
from loguru import logger
from fastapi import BackgroundTasks
from app.core.supabase import get_supabase_client
from app.core.qdrant import get_qdrant_client
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository
from app.connectors.connector_factory import ConnectorFactory
from app.services.ingestion_service import IngestionService

class SyncManager:
    def __init__(self, ingestion_service: IngestionService):
        self.ingest_svc = ingestion_service
        self.supabase = get_supabase_client()
        
        # Initialize vector repository
        qdrant_client = get_qdrant_client()
        self.vector_repo = VectorRepository(qdrant_client)

    def run_sync_for_folder(self, folder_row_id: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """
        Executes an incremental sync iteration for a specific configured folder.
        Uses provider delta change APIs, skipping unchanged files and re-indexing modified ones.
        """
        t_start = time.time()
        logger.info(f"SyncManager starting sync iteration for folder row {folder_row_id}...")
        
        # 1. Fetch folder config metadata
        folder_res = self.supabase.table("connector_folders").select("*").eq("id", folder_row_id).execute()
        if not folder_res.data:
            raise ValueError(f"Folder configuration not found: {folder_row_id}")
        folder_config = folder_res.data[0]
        
        account_id = folder_config["account_id"]
        folder_id = folder_config["folder_id"]
        last_delta_token = folder_config.get("last_delta_token")
        
        # 2. Fetch Account and Credentials
        account_res = self.supabase.table("connector_accounts").select("*").eq("id", account_id).execute()
        if not account_res.data:
            raise ValueError(f"Connector account not found: {account_id}")
        account = account_res.data[0]
        project_id = account["project_id"]
        provider = account["provider"]
        
        creds_res = self.supabase.table("connector_credentials").select("*").eq("account_id", account_id).execute()
        if not creds_res.data:
            raise ValueError(f"Credentials not found for account: {account_id}")
        creds = creds_res.data[0]
        
        access_token = creds["access_token"]
        refresh_token = creds["refresh_token"]
        
        # 3. Initialize sync job
        job_res = self.supabase.table("connector_sync_jobs").insert({
            "account_id": account_id,
            "status": "running"
        }).execute()
        job_id = job_res.data[0]["id"]
        
        files_added = 0
        files_updated = 0
        files_deleted = 0
        
        try:
            # 4. Resolve connector and query delta changes
            connector = ConnectorFactory.get_connector(provider, access_token=access_token)
            
            # If start token is missing, initialize starting page token
            if not last_delta_token:
                last_delta_token = "mock_gdrive_token_init" if provider == "google_drive" else ("mock_sp_token_init" if provider == "sharepoint" else "mock_od_token_init")
                
            logger.info(f"Retrieving incremental delta changes using token: {last_delta_token}")
            changed_files, deleted_ids, new_delta_token = connector.get_changes(
                folder_id=folder_id,
                start_token=last_delta_token
            )
            
            doc_repo = DocumentRepository(self.supabase)
            
            # 5. Process deleted files
            for del_file_id in deleted_ids:
                logger.info(f"Processing deleted file ID: {del_file_id}")
                # Retrieve logical document associated with this external file_id mapping
                # We can store the cloud file_id inside document_metadata in Supabase
                meta_res = self.supabase.table("document_metadata").select("document_id").eq("meta_key", "cloud_file_id").eq("meta_value", del_file_id).execute()
                if meta_res.data:
                    doc_id = meta_res.data[0]["document_id"]
                    logger.info(f"Incremental indexing: Deleting old vectors for document {doc_id}")
                    # Delete from Qdrant
                    self.vector_repo.delete_document_vectors("rag_documents", doc_id)
                    # Delete logical doc (this cascades and deletes revisions and metadata)
                    doc_repo.delete_document(doc_id)
                    
                    # Log sync log entry
                    self.supabase.table("connector_sync_logs").insert({
                        "job_id": job_id,
                        "file_id": del_file_id,
                        "filename": "Unknown (Deleted)",
                        "action": "deleted",
                        "status": "success"
                    }).execute()
                    files_deleted += 1
            
            # 6. Process added/modified files
            for file_meta in changed_files:
                f_id = file_meta["id"]
                f_name = file_meta["name"]
                f_mime = file_meta.get("mimeType", "application/octet-stream")
                
                logger.info(f"Downloading changed cloud file: '{f_name}' (ID: {f_id})")
                file_bytes = connector.download(f_id)
                
                # Check duplicate SHA256 checksum mapping
                hasher = hashlib.sha256(file_bytes)
                checksum = hasher.hexdigest()
                
                # See if document already exists
                logical_doc = doc_repo.get_document_by_name(project_id, f_name)
                
                if logical_doc:
                    # Document already indexed in project. Check if revision changed
                    latest_rev = doc_repo.get_latest_revision(logical_doc["id"])
                    if latest_rev and latest_rev["checksum"] == checksum:
                        logger.info(f"File '{f_name}' checksum unchanged. Skipping indexing.")
                        continue
                        
                    # File modified: Incremental Re-indexing
                    logger.info(f"Incremental Indexing: File '{f_name}' was modified. Removing old vectors...")
                    doc_id = logical_doc["id"]
                    self.vector_repo.delete_document_vectors("rag_documents", doc_id)
                    
                    # Delete revisions to prepare for reprocessing
                    self.supabase.table("document_revisions").delete().eq("document_id", doc_id).execute()
                    
                    action = "updated"
                    files_updated += 1
                else:
                    action = "added"
                    files_added += 1
                    
                # Buffer bytes to a stream and trigger Ingestion
                file_stream = io.BytesIO(file_bytes)
                
                # Determine revision number (Increment if updated, else start at A)
                rev_num = "A"
                if logical_doc and latest_rev:
                    try:
                        # Try to increment revision string, e.g. A -> B
                        curr_char = ord(latest_rev["revision_number"])
                        rev_num = chr(curr_char + 1)
                    except:
                        rev_num = "B"
                        
                logger.info(f"Registering ingestion task for '{f_name}' as Revision '{rev_num}'")
                ingest_res = self.ingest_svc.save_and_register_document(
                    project_id=project_id,
                    document_name=f_name,
                    document_type="specification" if "spec" in f_name.lower() else "drawing",
                    revision_number=rev_num,
                    file_stream=file_stream,
                    mime_type=f_mime,
                    user_id=account.get("account_email", "cloud_sync_service"),
                    background_tasks=background_tasks
                )
                
                # Insert external file_id mapping into document metadata for change tracking
                doc_id = ingest_res["document"]["id"]
                self.supabase.table("document_metadata").insert({
                    "document_id": doc_id,
                    "meta_key": "cloud_file_id",
                    "meta_value": f_id
                }).execute()
                
                # Log success
                self.supabase.table("connector_sync_logs").insert({
                    "job_id": job_id,
                    "file_id": f_id,
                    "filename": f_name,
                    "action": action,
                    "status": "success"
                }).execute()
                
            # 7. Update folder's start page token/delta link
            self.supabase.table("connector_folders").update({
                "last_delta_token": new_delta_token
            }).eq("id", folder_row_id).execute()
            
            # 8. Complete Sync Job successfully
            self.supabase.table("connector_sync_jobs").update({
                "status": "completed",
                "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "files_added": files_added,
                "files_updated": files_updated,
                "files_deleted": files_deleted
            }).eq("id", job_id).execute()
            
            duration = time.time() - t_start
            logger.info(f"[SUCCESS] SyncManager folder sync completed. Duration: {duration:.2f}s. Added: {files_added}, Updated: {files_updated}, Deleted: {files_deleted}")
            
            return {
                "status": "completed",
                "files_added": files_added,
                "files_updated": files_updated,
                "files_deleted": files_deleted,
                "duration_seconds": duration
            }
        except Exception as err:
            err_msg = str(err)
            logger.error(f"[FAILURE] SyncManager folder sync failed: {err_msg}")
            
            self.supabase.table("connector_sync_jobs").update({
                "status": "failed",
                "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error_message": err_msg
            }).eq("id", job_id).execute()
            
            raise RuntimeError(f"Sync execution failed: {err_msg}")
