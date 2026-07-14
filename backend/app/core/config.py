import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise Construction AI Document Intelligence Platform"
    API_V1_STR: str = "/api"
    
    # Supabase configuration
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_ANON_KEY: str = "your-supabase-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "your-supabase-service-key"
    
    # Qdrant configuration
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    # LLM configuration
    LLM_PROVIDER: str = "ollama"  # 'ollama', 'vllm', or 'openrouter'
    LLM_API_BASE: str = "http://localhost:11434/v1"
    LLM_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    LLM_MODEL: str = "qwen/qwen3-8b"
    
    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    # Development Demo Mode
    DEMO_MODE: bool = False

    
    # Allow loading from environment variable file (.env)
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
