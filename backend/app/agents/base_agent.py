from abc import ABC, abstractmethod

class BaseAgent(ABC):
    @abstractmethod
    def run(self, query: str, context: str = None) -> str:
        """Run the agent's prompt reasoning loop."""
        pass
