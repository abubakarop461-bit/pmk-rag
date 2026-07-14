from typing import Generator
from app.llm.base_llm import BaseLLM

class OllamaLLMProvider(BaseLLM):
    def __init__(self, host: str = "http://localhost:11434", model_name: str = "llama3"):
        self.host = host
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        # TODO: Implement local Ollama API call
        return f"[Ollama Placeholder Answer for: {prompt}]"

    def stream(self, prompt: str, system_prompt: str = None) -> Generator[str, None, None]:
        # TODO: Implement local Ollama streaming API call
        yield f"[Ollama Placeholder Stream: {prompt}]"

    def test_connection(self) -> bool:
        return False
