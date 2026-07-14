import os
from qdrant_client import QdrantClient
from app.core.config import settings
from loguru import logger

_qdrant_client = None

def get_qdrant_client() -> QdrantClient:
    """
    Returns an initialized cached singleton instance of QdrantClient.
    If remote connection fails, falls back seamlessly to a local disk-based database folder.
    """
    global _qdrant_client
    if _qdrant_client is None:
        # Check if settings suggest local mode, or if DEMO_MODE is true
        if settings.QDRANT_HOST.lower() in ["local", "memory", "none", ""] or settings.DEMO_MODE:
            logger.info("Configured to use local Qdrant database folder inside backend/qdrant_db...")
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qdrant_db")
            os.makedirs(db_path, exist_ok=True)
            _qdrant_client = QdrantClient(path=db_path)
        else:
            try:
                logger.info(f"Attempting connection to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}...")
                client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=2.0)
                # Test connectivity
                client.get_collections()
                _qdrant_client = client
                logger.info("[SUCCESS] Connected to remote Qdrant database server.")
            except Exception as e:
                logger.warning(f"Qdrant connection to {settings.QDRANT_HOST} failed: {e}. Falling back to local disk storage...")
                db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qdrant_db")
                os.makedirs(db_path, exist_ok=True)
                _qdrant_client = QdrantClient(path=db_path)
    return _qdrant_client
