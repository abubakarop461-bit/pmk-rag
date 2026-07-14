from abc import ABC, abstractmethod
from typing import List
from langchain_core.documents import Document

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> List[Document]:
        """Extract text from the file and return list of page-level Document objects."""
        pass
