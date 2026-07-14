from app.connectors.base_connector import BaseConnector

class GoogleDriveConnector(BaseConnector):
    def list_files(self) -> list:
        # TODO: Implement Google Drive API list traversal
        return []

    def download_file(self, file_id: str, download_path: str) -> str:
        # TODO: Implement Google Drive API file stream download
        return download_path
