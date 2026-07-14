from app.connectors.base_connector import BaseConnector

class SharePointConnector(BaseConnector):
    def list_files(self) -> list:
        # TODO: Implement SharePoint Graph API folder list traversal
        return []

    def download_file(self, file_id: str, download_path: str) -> str:
        # TODO: Implement SharePoint Graph API file stream download
        return download_path
