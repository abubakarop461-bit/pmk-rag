import os
from typing import Generator
from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Configure Loguru logger
logger.add(
    "rag_app.log",
    rotation="10 MB",
    retention="10 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Suggested OpenRouter models
SUGGESTED_MODELS = [
    "qwen/qwen3-8b",
    "meta-llama/llama-3.1-8b-instruct",
    "google/gemma-3-12b-it",
    "mistralai/mistral-small"
]

class OpenRouterLLMProvider:
    def __init__(
        self,
        api_key: str = None,
        model_name: str = "qwen/qwen3-8b",
        temperature: float = 0.0,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize the OpenRouter LLM Provider.
        Resolves the API key checking the input parameter, environment variable, or .env file.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model_name = model_name
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        self._llm = None

        if self.api_key:
            self._init_llm()
        else:
            logger.warning("OpenRouter API key is not configured yet. Initialize client after providing a key.")

    def _init_llm(self):
        """Initializes the ChatOpenAI client with OpenRouter's endpoint."""
        try:
            logger.info(f"Initializing OpenRouter client for model: {self.model_name}")
            self._llm = ChatOpenAI(
                openai_api_key=self.api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                model_name=self.model_name,
                temperature=self.temperature,
                timeout=self.timeout,
                max_retries=self.max_retries,
                default_headers={
                    "HTTP-Referer": "https://github.com/pmk-RAG",
                    "X-Title": "pmk-RAG Prototype",
                }
            )
            logger.info("OpenRouter client successfully initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize ChatOpenAI client for OpenRouter: {e}")
            raise

    def get_llm(self) -> ChatOpenAI:
        """Gets the underlying ChatOpenAI instance, initializing it if necessary."""
        if not self._llm:
            if not self.api_key:
                logger.error("Attempted to access LLM without an API key configured.")
                raise ValueError("OpenRouter API Key is missing. Please configure it.")
            self._init_llm()
        return self._llm

    def test_connection(self) -> bool:
        """Tests the connection to OpenRouter by sending a simple ping request."""
        try:
            llm = self.get_llm()
            logger.info("Testing connection to OpenRouter API...")
            response = llm.invoke("respond with only the word 'ok'")
            result = response.content.strip().lower()
            logger.info(f"Connection test response: {result}")
            return "ok" in result
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise

    def get_rag_prompt_template(self) -> ChatPromptTemplate:
        """Returns the prompt template with strict instructions as requested."""
        return ChatPromptTemplate.from_messages([
            ("system", (
                "Answer ONLY using the provided context. If the answer isn't in the context, "
                "say 'Not found in the provided documents.' Do not guess or fabricate. "
                "Never use outside knowledge. Always list source citations."
            )),
            ("user", "Context:\n{context}\n\nQuestion: {question}")
        ])

    def stream_answer(self, question: str, context: str) -> Generator[str, None, None]:
        """
        Streams the response tokens for a given question and retrieved context.
        Yields tokens as strings.
        """
        try:
            llm = self.get_llm()
            prompt_template = self.get_rag_prompt_template()
            
            # Construct Chain
            chain = prompt_template | llm | StrOutputParser()
            
            logger.info(f"Invoking streaming request for question: '{question}' using model '{self.model_name}'")
            for chunk in chain.stream({"context": context, "question": question}):
                yield chunk
        except Exception as e:
            logger.error(f"Error during OpenRouter streaming query: {e}")
            raise
