import os
import hashlib
import fitz  # PyMuPDF
from loguru import logger
from app.core.supabase import get_supabase_client
from app.core.qdrant import get_qdrant_client
from app.services.parser_service import ParserService
from app.services.metadata_service import MetadataService
from app.services.ocr_service import OcrService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.indexing_service import IndexingService
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository
from app.repositories.audit_repository import AuditRepository

def update_revision_status(
    client, 
    revision_id: str, 
    project_id: str, 
    status: str, 
    error_message: str = None, 
    timings: dict = None, 
    failed_stage: str = None
):
    """Updates the status and error details of a document revision in Supabase and publishes SSE events."""
    data = {"processing_status": status}
    if error_message:
        data["error_message"] = error_message
    if timings:
        data["processing_timings"] = timings
        
    client.table("document_revisions").update(data).eq("id", revision_id).execute()
    
    # Publish real-time event to SSE listeners
    try:
        from app.api.document import document_event_manager
        event_payload = {
            "revision_id": revision_id,
            "processing_status": status,
            "error_message": error_message,
            "failed_stage": failed_stage,
            "processing_timings": timings
        }
        document_event_manager.publish(project_id, event_payload)
    except Exception as sse_err:
        logger.warning(f"Failed to publish SSE event: {sse_err}")

def process_document_task(
    project_id: str,
    document_id: str,
    revision_id: str,
    file_path: str,
    document_name: str,
    document_type: str,
    revision_number: str,
    mime_type: str,
    user_id: str,
    upload_ms: int = 0
):
    """
    Ingestion pipeline worker executing asynchronously.
    Moves through validation -> parsing -> metadata -> OCR -> chunking -> embedding -> indexing -> ready.
    Supports system-wide duplicate vector reuse via cloning and parallel processing.
    """
    import time
    import datetime
    import traceback
    import json
    import threading
    import concurrent.futures
    
    start_time = time.time()
    timings = {"upload_ms": upload_ms}
    current_stage = "queued"
    
    logger.info(f"[JOB START] Processing document: '{document_name}' Rev '{revision_number}' (ID: {document_id})")
    
    # Initialize connection clients
    supabase_client = get_supabase_client()
    qdrant_client = get_qdrant_client()
    
    doc_repo = DocumentRepository(supabase_client)
    audit_repo = AuditRepository(supabase_client)
    vector_repo = VectorRepository(qdrant_client)
    
    parser_service = ParserService()
    metadata_service = MetadataService()
    ocr_service = OcrService()
    chunking_service = ChunkingService()
    embedding_service = EmbeddingService()
    indexing_service = IndexingService(vector_repo, chunking_service, embedding_service)
    
    # Transition: queued
    update_revision_status(supabase_client, revision_id, project_id, "queued")
    logger.info("Ingestion Task status: queued")
    
    try:
        # 1. FILE VALIDATIONS
        current_stage = "validating"
        val_start = time.time()
        update_revision_status(supabase_client, revision_id, project_id, "validating")
        logger.info("Ingestion Task status: validating")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError("Physical document binary was not saved to disk.")
            
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("Validation failed: Empty file detected.")
            
        if file_size > 50 * 1024 * 1024:
            raise ValueError("Validation failed: File size exceeds the maximum permitted limit of 50MB.")
            
        ext = os.path.splitext(file_path)[1].lower()
        allowed_extensions = [".pdf", ".docx", ".xlsx", ".xls", ".pptx", ".txt", ".jpg", ".jpeg", ".png"]
        if ext not in allowed_extensions:
            raise ValueError(f"Validation failed: Unsupported file extension '{ext}'. Permitted types: {allowed_extensions}")
            
        try:
            with open(file_path, "rb") as f_chk:
                header = f_chk.read(4)
                if not header:
                    raise ValueError("Empty header content.")
        except Exception as io_err:
            raise ValueError(f"Validation failed: Corrupted file detection triggered: {io_err}")
            
        # Get pre-computed checksum (which was saved by ingestion_service)
        rev_data_res = supabase_client.table("document_revisions").select("checksum").eq("id", revision_id).execute()
        if not rev_data_res.data or not rev_data_res.data[0].get("checksum"):
            # Compute fallback checksum if missing
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f_hash:
                for block in iter(lambda: f_hash.read(65536), b""):
                    hasher.update(block)
            checksum = hasher.hexdigest()
            supabase_client.table("document_revisions").update({"checksum": checksum}).eq("id", revision_id).execute()
        else:
            checksum = rev_data_res.data[0]["checksum"]
        
        # Check System-wide Duplicates
        existing_ready_rev = doc_repo.get_any_ready_revision_by_checksum(checksum)
        if existing_ready_rev:
            # Different project duplicate: Clone existing vectors in Qdrant and skip reprocessing completely
            logger.info(f"System-wide duplicate detected (checksum: {checksum}). Reusing existing embeddings by cloning vectors...")
            
            # Transition: indexing (to reflect Qdrant updates)
            current_stage = "indexing"
            update_revision_status(supabase_client, revision_id, project_id, "indexing")
            
            cloned_count = vector_repo.clone_document_vectors(
                collection_name="rag_documents",
                source_revision_id=existing_ready_rev["id"],
                target_project_id=project_id,
                target_document_id=document_id,
                target_revision_id=revision_id,
                target_filename=document_name
            )
            logger.info(f"Successfully cloned {cloned_count} vector points in Qdrant.")
            
            # Copy metadata in Supabase
            existing_metadata = supabase_client.table("document_metadata").select("*").eq("document_id", existing_ready_rev["document_id"]).execute()
            for row in existing_metadata.data:
                supabase_client.table("document_metadata").insert({
                    "document_id": document_id,
                    "meta_key": row["meta_key"],
                    "meta_value": row["meta_value"]
                }).execute()
                
            total_time_ms = int((time.time() - start_time) * 1000)
            timings.update({
                "validation_ms": int((time.time() - val_start) * 1000),
                "parsing_ms": 0,
                "ocr_ms": 0,
                "metadata_extraction_ms": 0,
                "chunking_ms": 0,
                "embedding_ms": 0,
                "indexing_ms": 0,
                "total_ms": total_time_ms
            })
            update_revision_status(supabase_client, revision_id, project_id, "ready", timings=timings)
            
            # Log success audit
            try:
                audit_repo.log_event(
                    user_id=user_id,
                    action="document_uploaded",
                    details={
                        "project_id": project_id,
                        "document_id": document_id,
                        "document_name": document_name,
                        "revision": revision_number,
                        "reused_embeddings": True,
                        "status": "ready"
                    }
                )
            except Exception as log_err:
                logger.warning(f"Failed to write upload audit log: {log_err}")
            return
            
        val_time = int((time.time() - val_start) * 1000)
        timings["validation_ms"] = val_time
        logger.info("[SUCCESS] Document file validation successful.")
        
        # 2. PARSING STAGE
        current_stage = "parsing"
        parse_start = time.time()
        update_revision_status(supabase_client, revision_id, project_id, "parsing")
        logger.info("Ingestion Task status: parsing")
        
        parsed_docs = parser_service.parse_file(file_path)
        parse_time = int((time.time() - parse_start) * 1000)
        timings["parsing_ms"] = parse_time
        
        # 3. METADATA EXTRACTION STAGE
        current_stage = "metadata_extraction"
        meta_start = time.time()
        update_revision_status(supabase_client, revision_id, project_id, "metadata_extraction")
        logger.info("Ingestion Task status: metadata_extraction")
        
        meta_payload = metadata_service.extract_metadata(
            file_path=file_path,
            mime_type=mime_type,
            doc_type=document_type,
            revision_number=revision_number,
            project_id=project_id,
            parsed_docs=parsed_docs
        )
        
        for key, val in meta_properties_to_save(meta_payload).items():
            supabase_client.table("document_metadata").delete().eq("document_id", document_id).eq("meta_key", key).execute()
            supabase_client.table("document_metadata").insert({
                "document_id": document_id,
                "meta_key": key,
                "meta_value": str(val)
            }).execute()
        meta_time = int((time.time() - meta_start) * 1000)
        timings["metadata_extraction_ms"] = meta_time
            
        # 4. OCR STAGE (with concurrency, smarter density checks, and caching)
        current_stage = "ocr"
        ocr_start = time.time()
        update_revision_status(supabase_client, revision_id, project_id, "ocr")
        logger.info("Ingestion Task status: ocr")
        
        from app.services.ocr_service import get_ocr_cache
        ocr_cache = get_ocr_cache()
        ocr_run_count = 0
        ocr_lock = threading.Lock()
        
        if ext == ".pdf":
            # Check page-by-page text density in PDF
            pdf_doc = fitz.open(file_path)
            num_pages = len(parsed_docs)
            
            def ocr_page_task(page_idx, page):
                nonlocal ocr_run_count
                text_len = len(page.page_content.strip())
                if text_len < 50:
                    cache_key = f"{checksum}_{page_idx}"
                    if cache_key in ocr_cache:
                        logger.info(f"Page {page_idx + 1} OCR hit cache.")
                        page.page_content = ocr_cache[cache_key]
                        return
                        
                    logger.info(f"Page {page_idx + 1} has low text density ({text_len} chars). Running OCR...")
                    # Open separate fitz document per thread for safety
                    thread_pdf = fitz.open(file_path)
                    try:
                        fitz_page = thread_pdf.load_page(page_idx)
                        pix = fitz_page.get_pixmap(dpi=150)
                        temp_img_path = os.path.join(os.path.dirname(file_path), f"temp_{revision_id}_{page_idx}.png")
                        pix.save(temp_img_path)
                    finally:
                        thread_pdf.close()
                        
                    try:
                        ocr_text = ocr_service.ocr_image(temp_img_path)
                        page.page_content = ocr_text
                        ocr_cache[cache_key] = ocr_text
                        with ocr_lock:
                            ocr_run_count += 1
                    finally:
                        if os.path.exists(temp_img_path):
                            os.remove(temp_img_path)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(max(num_pages, 1), 4)) as ocr_executor:
                list(ocr_executor.map(lambda item: ocr_page_task(item[0], item[1]), enumerate(parsed_docs)))
            pdf_doc.close()
            
        elif ext in [".jpg", ".jpeg", ".png"]:
            cache_key = f"{checksum}_0"
            if cache_key in ocr_cache:
                logger.info("Image OCR hit cache.")
                if parsed_docs:
                    parsed_docs[0].page_content = ocr_cache[cache_key]
            else:
                logger.info("Processing visual image file. Executing OCR pipeline...")
                ocr_text = ocr_service.ocr_image(file_path)
                ocr_cache[cache_key] = ocr_text
                if parsed_docs:
                    parsed_docs[0].page_content = ocr_text
                    ocr_run_count += 1
                
        ocr_time = int((time.time() - ocr_start) * 1000)
        timings["ocr_ms"] = ocr_time
        logger.info(f"OCR stage completed. OCR executed on {ocr_run_count} pages.")
        
        # 5. CHUNKING STAGE
        current_stage = "chunking"
        update_revision_status(supabase_client, revision_id, project_id, "chunking")
        logger.info("Ingestion Task status: chunking")
        
        # 6. EMBEDDING STAGE
        current_stage = "embedding"
        update_revision_status(supabase_client, revision_id, project_id, "embedding")
        logger.info("Ingestion Task status: embedding")
        
        # 7. INDEXING STAGE
        current_stage = "indexing"
        update_revision_status(supabase_client, revision_id, project_id, "indexing")
        logger.info("Ingestion Task status: indexing")
        
        idx_timings = indexing_service.index_document_pages(
            project_id=project_id,
            document_id=document_id,
            revision_id=revision_id,
            document_type=document_type,
            filename=document_name,
            pages=parsed_docs,
            extra_metadata=meta_payload
        )
        timings.update(idx_timings)
        
        # 8. READY STAGE
        total_time_ms = int((time.time() - start_time) * 1000)
        timings["total_ms"] = total_time_ms
        
        update_revision_status(supabase_client, revision_id, project_id, "ready", timings=timings)
        logger.info("[SUCCESS] Document ingestion completed and indexed in Qdrant.")
        
    except Exception as err:
        tb = traceback.format_exc()
        err_msg = str(err)
        logger.error(f"[FAILURE] Document processing failed: {err_msg}")
        
        error_details = {
            "failed_stage": current_stage,
            "exception": err_msg,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "stack_trace": tb
        }
        error_str = json.dumps(error_details)
        
        # Transition: failed
        update_revision_status(
            client=supabase_client,
            revision_id=revision_id,
            project_id=project_id,
            status="failed",
            error_message=error_str,
            failed_stage=current_stage
        )
        
        # Write failure audit log
        try:
            audit_repo.log_action(
                user_id=user_id,
                action="document_validation_failed" if "validation" in err_msg.lower() else "document_indexing_failed",
                details={
                    "project_id": project_id,
                    "document_id": document_id,
                    "document_name": document_name,
                    "revision": revision_number,
                    "error": err_msg
                }
            )
        except Exception as log_err:
            logger.warning(f"Failed to write failure audit log: {log_err}")


def meta_properties_to_save(meta: dict) -> dict:
    """Filter out internal keys that are saved in columns anyway."""
    exclude_keys = ["document_type", "revision", "project_id"]
    return {k: v for k, v in meta.items() if k not in exclude_keys}
