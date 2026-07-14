from app.connectors.base_connector import BaseConnector

class OneDriveConnector(BaseConnector):
    def list_files(self) -> list:
        # TODO: Implement OneDrive Graph API file traversal
        return []

    def download_file(self, file_id: str, download_path: str) -> str:
        # TODO: Implement OneDrive Graph API file stream download
        return download_path
