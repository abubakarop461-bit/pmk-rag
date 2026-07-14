import os
from typing import List
from loguru import logger
from langchain_community.embeddings import HuggingFaceEmbeddings

_embeddings_instance = None

class EmbeddingService:
    def __init__(self):
        pass

    def get_embeddings_model(self) -> HuggingFaceEmbeddings:
        global _embeddings_instance
        if _embeddings_instance is None:
            logger.info("Initializing global HuggingFaceEmbeddings with BAAI/bge-small-en-v1.5...")
            _embeddings_instance = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-en-v1.5",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True}
            )
        return _embeddings_instance

    def embed_text(self, text: str) -> List[float]:
        model = self.get_embeddings_model()
        return model.embed_query(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings in batch for a list of texts."""
        if not texts:
            return []
        model = self.get_embeddings_model()
        return model.embed_documents(texts)
