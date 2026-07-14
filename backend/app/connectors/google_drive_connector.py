import httpx
from typing import List, Dict, Any, Tuple, Optional
from app.connectors.base_connector import BaseConnector
from app.connectors.connector_registry import ConnectorRegistry
from loguru import logger

@ConnectorRegistry.register("google_drive")
class GoogleDriveConnector(BaseConnector):
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.is_mock = not access_token or access_token.lower() == "mock"

    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """
        Exchanges Google auth authorization code for tokens.
        """
        if auth_code == "mock_code":
            return {
                "access_token": "mock_access_token",
                "refresh_token": "mock_refresh_token",
                "token_expires_at": "2030-01-01T00:00:00Z",
                "account_email": "engineer@pmk-rag.com"
            }
            
        url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": auth_code,
            "client_id": "google_drive_mock_client_id",
            "client_secret": "google_drive_mock_client_secret",
            "redirect_uri": "http://localhost:3000/settings",
            "grant_type": "authorization_code"
        }
        try:
            res = httpx.post(url, data=payload)
            res.raise_for_status()
            data = res.json()
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "token_expires_at": data.get("expires_in"),
                "account_email": "google_drive_connected_account@gmail.com"
            }
        except Exception as e:
            logger.error(f"Google Drive OAuth authenticate failed: {e}")
            raise RuntimeError(f"Authentication failed: {e}")

    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refreshes the Google access token.
        """
        if refresh_token == "mock_refresh_token":
            return {
                "access_token": "mock_access_token_refreshed",
                "token_expires_at": "2030-01-01T00:00:00Z"
            }
            
        url = "https://oauth2.googleapis.com/token"
        payload = {
            "refresh_token": refresh_token,
            "client_id": "google_drive_mock_client_id",
            "client_secret": "google_drive_mock_client_secret",
            "grant_type": "refresh_token"
        }
        try:
            res = httpx.post(url, data=payload)
            res.raise_for_status()
            data = res.json()
            return {
                "access_token": data["access_token"],
                "token_expires_at": data.get("expires_in")
            }
        except Exception as e:
            logger.error(f"Google Drive token refresh failed: {e}")
            raise RuntimeError(f"Refresh failed: {e}")

    def list_folders(self, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists folders inside the designated Google Drive scope.
        """
        if self.is_mock:
            return [
                {"id": "mock_gdrive_folder_root", "name": "Google Drive Main Construction Spec Folder"},
                {"id": "mock_gdrive_folder_drawings", "name": "Basement Civil Drawings Collection"}
            ]
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        url = f"https://www.googleapis.com/drive/v3/files?q={httpx.URLEscape(query)}&fields=files(id,name)"
        try:
            res = httpx.get(url, headers=headers)
            res.raise_for_status()
            return res.json().get("files", [])
        except Exception as e:
            logger.error(f"Google Drive list_folders failed: {e}")
            return []

    def list_documents(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        Lists files inside the folder_id.
        """
        if self.is_mock:
            return [
                {"id": "mock_gdrive_file_1", "name": "gdrive_concrete_spec.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-07-13T00:00:00Z"},
                {"id": "mock_gdrive_file_2", "name": "gdrive_site_report.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "modifiedTime": "2026-07-13T00:00:00Z"}
            ]
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
        url = f"https://www.googleapis.com/drive/v3/files?q={httpx.URLEscape(query)}&fields=files(id,name,mimeType,modifiedTime)"
        try:
            res = httpx.get(url, headers=headers)
            res.raise_for_status()
            return res.json().get("files", [])
        except Exception as e:
            logger.error(f"Google Drive list_documents failed: {e}")
            return []

    def download(self, file_id: str) -> bytes:
        """
        Downloads a file's raw byte payload from Google Drive.
        """
        if self.is_mock:
            # Return dummy bytes depending on the file
            if "file_1" in file_id:
                # Let's return a simple valid text/pdf placeholder header
                return b"%PDF-1.4 mock pdf structure bytes spec concrete curing wet burlap 7 days"
            return b"mock file docx text content specifications requirement basement column grid"
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        try:
            res = httpx.get(url, headers=headers)
            res.raise_for_status()
            return res.content
        except Exception as e:
            logger.error(f"Google Drive download failed: {e}")
            raise RuntimeError(f"Download failed: {e}")

    def get_changes(self, folder_id: str, start_token: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str], str]:
        """
        Uses Google Changes API.
        Returns: (changed_files, deleted_file_ids, new_start_token)
        """
        if self.is_mock:
            # Simulate Changes API states using start_token
            # If start_token is "mock_gdrive_token_init", return first-run files list
            if start_token == "mock_gdrive_token_init":
                files = [
                    {"id": "mock_gdrive_file_1", "name": "gdrive_concrete_spec.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-07-13T00:00:00Z"},
                    {"id": "mock_gdrive_file_2", "name": "gdrive_site_report.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "modifiedTime": "2026-07-13T00:00:00Z"}
                ]
                return files, [], "mock_gdrive_token_version_2"
                
            # If start_token is "mock_gdrive_token_version_2", simulate a modification of file_1 and deletion of file_2!
            elif start_token == "mock_gdrive_token_version_2":
                changed = [
                    {"id": "mock_gdrive_file_1", "name": "gdrive_concrete_spec.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-07-13T12:00:00Z"}
                ]
                deleted = ["mock_gdrive_file_2"]
                return changed, deleted, "mock_gdrive_token_version_3"
                
            return [], [], "mock_gdrive_token_version_3"
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. Get start token if missing
        if not start_token:
            start_url = "https://www.googleapis.com/drive/v3/changes/startPageToken"
            try:
                res = httpx.get(start_url, headers=headers)
                res.raise_for_status()
                start_token = res.json().get("startPageToken", "1")
            except Exception as e:
                logger.error(f"Google Drive start page token fetch failed: {e}")
                return [], [], "1"
                
        # 2. Get changes list
        url = f"https://www.googleapis.com/drive/v3/changes?pageToken={start_token}&fields=newStartPageToken,changes(fileId,removed,file(id,name,mimeType,modifiedTime,parents))"
        try:
            res = httpx.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()
            new_token = data.get("newStartPageToken", start_token)
            
            changed_files = []
            deleted_ids = []
            
            for change in data.get("changes", []):
                file_id = change.get("fileId")
                if change.get("removed"):
                    deleted_ids.append(file_id)
                else:
                    gfile = change.get("file", {})
                    # Ensure it belongs to our synced folder
                    parents = gfile.get("parents", [])
                    if folder_id in parents:
                        changed_files.append({
                            "id": gfile.get("id"),
                            "name": gfile.get("name"),
                            "mimeType": gfile.get("mimeType"),
                            "modifiedTime": gfile.get("modifiedTime")
                        })
            return changed_files, deleted_ids, new_token
        except Exception as e:
            logger.error(f"Google Drive changes list failed: {e}")
            return [], [], start_token
