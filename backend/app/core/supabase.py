from supabase import create_client, Client
from app.core.config import settings
from loguru import logger

_supabase_client: Client = None

def get_supabase_client() -> Client:
    """
    Retrieves or initializes a singleton Supabase client.
    Normalizes URLs by stripping trailing REST suffixes.
    Fails gracefully if credentials are missing or default placeholders.
    """
    global _supabase_client
    if _supabase_client is None:
        url = settings.SUPABASE_URL.strip() if settings.SUPABASE_URL else ""
        
        # Normalize the URL by stripping "/rest/v1/" suffix if present
        if url.endswith("/rest/v1/"):
            url = url[:-9]
        elif url.endswith("/rest/v1"):
            url = url[:-8]
        if url.endswith("/"):
            url = url[:-1]

        # Prefer service_role_key for backend admin operations, fall back to anon_key
        key = settings.SUPABASE_SERVICE_ROLE_KEY.strip() if settings.SUPABASE_SERVICE_ROLE_KEY else ""
        if not key:
            key = settings.SUPABASE_ANON_KEY.strip() if settings.SUPABASE_ANON_KEY else ""
            
        # Validation checks for missing or placeholder parameters
        if not url or "your-project" in url:
            logger.warning("[WARNING] SUPABASE_URL environment variable is missing or set to placeholder.")
            raise ValueError("SUPABASE_URL is missing or set to placeholder.")
            
        if not key or "your-supabase" in key:
            logger.warning("[WARNING] Supabase API key is missing or set to placeholder.")
            raise ValueError("Supabase API keys are missing or set to placeholders.")
            
        try:
            logger.info(f"Initializing singleton Supabase client for project base URL: {url}")
            _supabase_client = create_client(url, key)
            logger.info("[SUCCESS] Supabase client connection established.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize Supabase client: {e}")
            raise RuntimeError(f"Supabase client initialization failed: {e}")
            
    return _supabase_client
