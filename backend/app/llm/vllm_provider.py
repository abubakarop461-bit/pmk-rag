from typing import Generator
from app.llm.base_llm import BaseLLM

class VllmLLMProvider(BaseLLM):
    def __init__(self, endpoint: str = "http://localhost:8000/v1", model_name: str = "qwen2"):
        self.endpoint = endpoint
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        # TODO: Implement OpenAI-compatible vLLM server completions
        return f"[vLLM Placeholder Answer for: {prompt}]"

    def stream(self, prompt: str, system_prompt: str = None) -> Generator[str, None, None]:
        # TODO: Implement OpenAI-compatible vLLM server streaming completions
        yield f"[vLLM Placeholder Stream: {prompt}]"

    def test_connection(self) -> bool:
        return False
