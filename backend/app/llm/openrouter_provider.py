from typing import Generator
from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.llm.base_llm import BaseLLM

class OpenRouterLLMProvider(BaseLLM):
    def __init__(self, api_key: str, model_name: str = "qwen/qwen3-8b"):
        self.api_key = api_key
        self.model_name = model_name
        self._llm = None
        
        if self.api_key:
            self._init_client()

    def _init_client(self):
        try:
            self._llm = ChatOpenAI(
                openai_api_key=self.api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                model_name=self.model_name,
                default_headers={
                    "HTTP-Referer": "https://github.com/pmk-RAG",
                    "X-Title": "Enterprise Construction RAG",
                }
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChatOpenAI client for OpenRouter: {e}")
            raise

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self._llm:
            self._init_client()
        
        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("user", prompt))
        
        prompt_tmpl = ChatPromptTemplate.from_messages(messages)
        chain = prompt_tmpl | self._llm | StrOutputParser()
        return chain.invoke({})

    def stream(self, prompt: str, system_prompt: str = None) -> Generator[str, None, None]:
        if not self._llm:
            self._init_client()
            
        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("user", prompt))
        
        prompt_tmpl = ChatPromptTemplate.from_messages(messages)
        chain = prompt_tmpl | self._llm | StrOutputParser()
        yield from chain.stream({})

    def test_connection(self) -> bool:
        try:
            res = self.generate("respond with only the word 'ok'")
            return "ok" in res.lower()
        except Exception as e:
            logger.error(f"OpenRouter connection test failed: {e}")
            return False
