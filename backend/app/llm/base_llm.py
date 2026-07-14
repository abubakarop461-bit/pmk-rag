from abc import ABC, abstractmethod
from typing import Generator

class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate a complete response string for the prompt."""
        pass

    @abstractmethod
    def stream(self, prompt: str, system_prompt: str = None) -> Generator[str, None, None]:
        """Stream response tokens for the prompt."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test LLM API connection status."""
        pass
