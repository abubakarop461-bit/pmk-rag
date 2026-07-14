import httpx
from typing import List, Dict, Any, Tuple, Optional
from app.connectors.base_connector import BaseConnector
from app.connectors.connector_registry import ConnectorRegistry
from loguru import logger

@ConnectorRegistry.register("sharepoint")
class SharePointConnector(BaseConnector):
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.is_mock = not access_token or access_token.lower() == "mock"

    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """
        Exchanges SharePoint auth code for access & refresh tokens.
        """
        return {
            "access_token": "mock_sharepoint_access_token",
            "refresh_token": "mock_sharepoint_refresh_token",
            "token_expires_at": "2030-01-01T00:00:00Z",
            "account_email": "sharepoint_admin@pmk-rag.onmicrosoft.com"
        }

    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        return {
            "access_token": "mock_sharepoint_access_token_refreshed",
            "token_expires_at": "2030-01-01T00:00:00Z"
        }

    def list_folders(self, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists folders inside SharePoint Document Library.
        """
        if self.is_mock:
            return [
                {"id": "mock_sp_folder_root", "name": "SharePoint Construction Document Library"},
                {"id": "mock_sp_folder_records", "name": "Architectural Design Records"}
            ]
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        # Fetch root items
        url = "https://graph.microsoft.com/v1.0/sites/root/drives"
        try:
            res = httpx.get(url, headers=headers)
            res.raise_for_status()
            drives = res.json().get("value", [])
            # For simplicity, query the first document library
            if drives:
                drive_id = drives[0]["id"]
                target_id = folder_id or "root"
                items_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{target_id}/children"
                res_items = httpx.get(items_url, headers=headers)
                res_items.raise_for_status()
                return [
                    {"id": item["id"], "name": item["name"]}
                    for item in res_items.json().get("value", [])
                    if "folder" in item
                ]
            return []
        except Exception as e:
            logger.error(f"SharePoint list_folders failed: {e}")
            return []

    def list_documents(self, folder_id: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            return [
                {"id": "mock_sp_file_1", "name": "sharepoint_spec_curing.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-07-13T00:00:00Z"},
            ]
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        # Hardcoded to search active drives children
        url = f"https://graph.microsoft.com/v1.0/drives/mock_drive_id/items/{folder_id}/children"
        try:
            res = httpx.get(url, headers=headers)
            res.raise_for_status()
            return [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "mimeType": item.get("file", {}).get("mimeType", "application/octet-stream"),
                    "modifiedTime": item.get("lastModifiedDateTime")
                }
                for item in res.json().get("value", [])
                if "folder" not in item
            ]
        except Exception as e:
            logger.error(f"SharePoint list_documents failed: {e}")
            return []

    def download(self, file_id: str) -> bytes:
        if self.is_mock:
            return b"%PDF-1.4 mock sharepoint spec concrete curing wet burlap 7 days"
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"https://graph.microsoft.com/v1.0/drives/mock_drive_id/items/{file_id}/content"
        try:
            res = httpx.get(url, headers=headers)
            res.raise_for_status()
            return res.content
        except Exception as e:
            logger.error(f"SharePoint download failed: {e}")
            raise RuntimeError(f"Download failed: {e}")

    def get_changes(self, folder_id: str, start_token: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str], str]:
        """
        Uses Microsoft Graph Delta API.
        Returns: (changed_files, deleted_file_ids, new_start_token)
        """
        if self.is_mock:
            if start_token == "mock_sp_token_init":
                files = [
                    {"id": "mock_sp_file_1", "name": "sharepoint_spec_curing.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-07-13T00:00:00Z"},
                ]
                return files, [], "mock_sp_token_version_2"
            elif start_token == "mock_sp_token_version_2":
                return [], [], "mock_sp_token_version_3"
            return [], [], "mock_sp_token_version_3"
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        # If no start token is stored, call delta on folder root
        query_url = start_token or f"https://graph.microsoft.com/v1.0/drives/mock_drive_id/items/{folder_id}/delta"
        
        try:
            res = httpx.get(query_url, headers=headers)
            res.raise_for_status()
            data = res.json()
            
            changed_files = []
            deleted_ids = []
            
            for item in data.get("value", []):
                file_id = item.get("id")
                if "removed" in item:
                    deleted_ids.append(file_id)
                elif "folder" not in item:
                    changed_files.append({
                        "id": file_id,
                        "name": item.get("name"),
                        "mimeType": item.get("file", {}).get("mimeType", "application/octet-stream"),
                        "modifiedTime": item.get("lastModifiedDateTime")
                    })
                    
            # MS Graph returns next link or delta link
            next_delta_link = data.get("@odata.deltaLink", query_url)
            return changed_files, deleted_ids, next_delta_link
        except Exception as e:
            logger.error(f"SharePoint delta sync failed: {e}")
            return [], [], start_token
