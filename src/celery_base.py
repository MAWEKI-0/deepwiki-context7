from celery import Task
from src.config import Settings
from src.dependencies import get_supabase, create_gemini_flash_client, create_gemini_pro_client, create_embedding_model_client
from supabase import Client as SupabaseClient
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

class BaseTaskWithClients(Task):
    """
    Base Celery Task class that initializes clients once per worker process.
    """
    def __init__(self):
        super().__init__()
        self._settings = Settings()
        self._supabase_client = get_supabase()
        self._gemini_flash_client = create_gemini_flash_client(self._settings)
        self._gemini_pro_client = create_gemini_pro_client(self._settings)
        self._embedding_model_instance = create_embedding_model_client(self._settings)

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def supabase_client(self) -> SupabaseClient:
        return self._supabase_client

    @property
    def gemini_flash_client(self) -> ChatGoogleGenerativeAI:
        return self._gemini_flash_client

    @property
    def gemini_pro_client(self) -> ChatGoogleGenerativeAI:
        return self._gemini_pro_client

    @property
    def embedding_model_instance(self) -> GoogleGenerativeAIEmbeddings:
        return self._embedding_model_instance
