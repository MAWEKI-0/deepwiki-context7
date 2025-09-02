import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Build a path to the .env file from the project root.
# This assumes config.py is in src/ and .env is in the parent directory.
env_path = Path(__file__).parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=env_path, extra="ignore")

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_CONNECTION_STRING: str

    # Google AI
    GOOGLE_API_KEY: str
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_PRO_MODEL: str = "gemini-2.5-flash-lite"

    # Embedding Model
    EMBEDDING_MODEL: str = "text-embedding-004" # Or other suitable embedding model

    # Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = False
    LOG_FILE: Optional[str] = "logs/app.log"
