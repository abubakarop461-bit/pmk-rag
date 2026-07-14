import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.supabase import get_supabase_client

# Initialize loguru
setup_logging()

# Global connection status trackers
qdrant_status = "disconnected"
supabase_status = "disconnected"
embedding_status = "disconnected"
reranker_status = "disconnected"
paddle_ocr_status = "disconnected"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global qdrant_status, supabase_status, embedding_status, reranker_status, paddle_ocr_status
    
    logger.info("Initializing Enterprise Construction AI Backend Service...")
    
    # 1. Verify Qdrant connection (supporting fallback)
    try:
        from app.core.qdrant import get_qdrant_client
        logger.info("Initializing Qdrant client connection...")
        q_client = get_qdrant_client()
        # Test connection
        q_client.get_collections()
        qdrant_status = "connected"
        logger.info("[SUCCESS] Qdrant connection verified.")
    except Exception as e:
        qdrant_status = f"error: {str(e)}"
        logger.warning(f"[FAILURE] Qdrant connection failed: {e}")
        
    # 2. Verify Supabase connection
    try:
        logger.info("Attempting connection check with Supabase...")
        s_client = get_supabase_client()
        
        # Test by running a lightweight projects query.
        try:
            s_client.table("projects").select("id").limit(1).execute()
            supabase_status = "connected"
            logger.info("[SUCCESS] Supabase connection verified.")
        except Exception as table_err:
            err_msg = str(table_err)
            if "relation" in err_msg or "schema cache" in err_msg or "PGRST205" in err_msg:
                supabase_status = "connected (schema missing)"
                logger.info("[SUCCESS] Supabase connection verified (tables not yet initialized).")
            else:
                raise table_err
                
    except Exception as e:
        supabase_status = f"error: {str(e)}"
        logger.warning(f"[FAILURE] Supabase connection failed: {e}")

    # 3. Pre-load AI Model Singletons
    try:
        logger.info("Pre-loading AI model singletons during startup...")
        from app.services.embedding_service import EmbeddingService
        from app.services.ocr_service import OcrService
        from app.services.reranker_service import get_reranker
        
        logger.info("Loading Embedding model (BAAI/bge-small-en-v1.5)...")
        try:
            EmbeddingService().get_embeddings_model()
            embedding_status = "loaded"
        except Exception as e:
            embedding_status = f"error: {str(e)}"
            logger.error(f"Failed to load Embedding model: {e}")
            raise e
            
        logger.info("Loading Reranker model (BAAI/bge-reranker-base)...")
        try:
            get_reranker()
            reranker_status = "loaded"
        except Exception as e:
            reranker_status = f"error: {str(e)}"
            logger.error(f"Failed to load Reranker model: {e}")
            raise e
            
        logger.info("Loading PaddleOCR engine...")
        try:
            OcrService()._init_paddle()
            from app.services.ocr_service import _paddle_ocr_instance
            if _paddle_ocr_instance:
                paddle_ocr_status = "loaded"
            else:
                paddle_ocr_status = "loaded (Tesseract fallback)"
        except Exception as e:
            paddle_ocr_status = f"error: {str(e)}"
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise e
            
        logger.info("[SUCCESS] All AI models pre-loaded successfully.")
    except Exception as model_err:
        logger.warning(f"Failed to pre-load some AI models during startup: {model_err}")

    # 4. Initialize Background Job Queue Manager worker threads
    try:
        from app.background.local_queue import BackgroundJobManager
        BackgroundJobManager()
        logger.info("[SUCCESS] BackgroundJobManager initialized with worker threads.")
    except Exception as queue_err:
        logger.warning(f"Failed to initialize BackgroundJobManager: {queue_err}")

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api.auth import router as auth_router
from app.api.project import router as project_router
from app.api.document import router as document_router
from app.api.retrieval import router as retrieval_router
from app.api.chat import router as chat_router
from app.api.connectors import router as connectors_router

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(project_router, prefix=settings.API_V1_STR)
app.include_router(document_router, prefix=settings.API_V1_STR)
app.include_router(retrieval_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(connectors_router, prefix=settings.API_V1_STR)

@app.get("/api/health")
async def health_check():
    # Keep status healthy if FastAPI is responding, but list database states inside services
    return {
        "status": "healthy",
        "services": {
            "supabase": supabase_status,
            "qdrant": qdrant_status,
            "embedding_model": embedding_status,
            "reranker": reranker_status,
            "paddle_ocr": paddle_ocr_status
        }
    }
