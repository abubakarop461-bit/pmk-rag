from abc import ABC, abstractmethod
from typing import BinaryIO

class BaseStorage(ABC):
    @abstractmethod
    def save(self, file_stream: BinaryIO, filename: str) -> str:
        """Save a file stream and return its location URI."""
        pass

    @abstractmethod
    def delete(self, filename: str) -> bool:
        """Delete a file by name."""
        pass
