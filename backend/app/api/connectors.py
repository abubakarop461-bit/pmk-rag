from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from typing import List, Dict, Any, Optional
from loguru import logger
from pydantic import BaseModel
from app.core.supabase import get_supabase_client
from app.repositories.document_repository import DocumentRepository
from app.storage.storage_service import LocalStorageService
from app.services.audit_service import AuditService
from app.services.ingestion_service import IngestionService
from app.services.sync_manager import SyncManager
from app.api.auth import get_current_user
from app.connectors.connector_factory import ConnectorFactory

router = APIRouter(prefix="/connectors", tags=["connectors"])

# Request/Response schemas
class ConnectAccountRequest(BaseModel):
    project_id: str
    provider: str
    auth_code: str
    account_email: str

class ConfigureFolderRequest(BaseModel):
    account_id: str
    folder_id: str
    folder_name: str

def get_sync_manager() -> SyncManager:
    db = get_supabase_client()
    doc_repo = DocumentRepository(db)
    storage = LocalStorageService()
    audit = AuditService(db)
    ingest = IngestionService(doc_repo, storage, audit)
    return SyncManager(ingest)

@router.post("/connect", status_code=status.HTTP_201_CREATED)
async def connect_account(request: ConnectAccountRequest, current_user: dict = Depends(get_current_user)):
    """
    Connects a new cloud provider account using OAuth auth_code.
    Splits credentials (access/refresh token) into connector_credentials.
    """
    db = get_supabase_client()
    try:
        # Resolve connector class dynamically via dynamic registry
        connector = ConnectorFactory.get_connector(request.provider)
        auth_data = connector.authenticate(request.auth_code)
        
        # 1. Insert Connector Account Metadata
        acc_res = db.table("connector_accounts").insert({
            "project_id": request.project_id,
            "provider": request.provider,
            "account_email": request.account_email or auth_data["account_email"],
            "status": "connected"
        }).execute()
        
        account_id = acc_res.data[0]["id"]
        
        # 2. Insert Connector Credentials (split table)
        db.table("connector_credentials").insert({
            "account_id": account_id,
            "access_token": auth_data["access_token"],
            "refresh_token": auth_data.get("refresh_token"),
            "token_expires_at": auth_data.get("token_expires_at")
        }).execute()
        
        return {"account_id": account_id, "status": "connected"}
    except Exception as e:
        logger.error(f"Failed to connect account: {e}")
        raise HTTPException(status_code=550, detail=f"Failed to connect cloud account: {e}")

@router.get("/accounts")
async def list_accounts(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    Lists all connected cloud accounts scoped for a project.
    """
    db = get_supabase_client()
    res = db.table("connector_accounts").select("*").eq("project_id", project_id).execute()
    return res.data or []

@router.get("/folders/list")
async def list_cloud_folders(account_id: str, folder_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """
    Queries the cloud provider dynamically to show directories available for sync mapping.
    """
    db = get_supabase_client()
    
    # Get account provider
    acc_res = db.table("connector_accounts").select("*").eq("id", account_id).execute()
    if not acc_res.data:
        raise HTTPException(status_code=404, detail="Account not found.")
    account = acc_res.data[0]
    
    # Get credentials
    creds_res = db.table("connector_credentials").select("access_token").eq("account_id", account_id).execute()
    if not creds_res.data:
        raise HTTPException(status_code=404, detail="Credentials not found.")
    
    access_token = creds_res.data[0]["access_token"]
    
    # Resolve connector instance dynamically
    connector = ConnectorFactory.get_connector(account["provider"], access_token=access_token)
    folders = connector.list_folders(folder_id)
    return folders

@router.post("/folders/configure")
async def configure_folder(request: ConfigureFolderRequest, current_user: dict = Depends(get_current_user)):
    """
    Binds a selected cloud directory to sync target folder mappings.
    """
    db = get_supabase_client()
    try:
        res = db.table("connector_folders").insert({
            "account_id": request.account_id,
            "folder_id": request.folder_id,
            "folder_name": request.folder_name,
            "sync_enabled": True
        }).execute()
        return res.data[0]
    except Exception as e:
        logger.error(f"Failed to configure folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/manual")
async def trigger_manual_sync(
    folder_id: str, 
    background_tasks: BackgroundTasks, 
    sync_mgr: SyncManager = Depends(get_sync_manager),
    current_user: dict = Depends(get_current_user)
):
    """
    Triggers an asynchronous synchronization job in FastAPI BackgroundTasks thread.
    """
    background_tasks.add_task(sync_mgr.run_sync_for_folder, folder_id, background_tasks)
    return {"message": "Sync job enqueued successfully in background."}

@router.get("/sync/jobs")
async def get_sync_history(account_id: str, current_user: dict = Depends(get_current_user)):
    """
    Retrieves previous synchronization audits history.
    """
    db = get_supabase_client()
    res = db.table("connector_sync_jobs").select("*").eq("account_id", account_id).order("created_at", desc=True).execute()
    return res.data or []
