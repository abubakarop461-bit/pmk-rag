from abc import ABC, abstractmethod
from typing import Callable, Any

class BaseJobQueue(ABC):
    @abstractmethod
    def enqueue(self, job_func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """
        Pushes a task onto the background execution queue.
        Returns a unique job identifier string immediately.
        """
        pass
