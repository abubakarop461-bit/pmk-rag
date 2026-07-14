from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional

class BaseConnector(ABC):
    @abstractmethod
    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """
        Exchanges code for credentials (tokens) and returns credentials metadata dict.
        """
        pass

    @abstractmethod
    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refreshes access tokens using refresh token.
        """
        pass

    @abstractmethod
    def list_folders(self, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists child folders within folder_id (or root if None) for selection.
        """
        pass

    @abstractmethod
    def list_documents(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        Lists all document files inside a folder.
        """
        pass

    @abstractmethod
    def download(self, file_id: str) -> bytes:
        """
        Downloads a file and returns its raw binary payload.
        """
        pass

    @abstractmethod
    def get_changes(self, folder_id: str, start_token: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str], str]:
        """
        Retrieves incremental updates (Delta/Changes API).
        Returns a tuple: (changed_files_list, deleted_file_ids_list, new_start_token)
        """
        pass
