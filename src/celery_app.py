from celery import Celery, Task
from src.config import Settings
from src.dependencies import get_settings, get_supabase_client, get_gemini_flash, get_gemini_pro, get_embedding_model
from src.logger import logger

class EnrichmentTask(Task):
    """
    Custom Celery Task class to manage client instances.
    Clients are initialized once per worker process, not per task.
    """
    _supabase = None
    _gemini_flash = None
    _gemini_pro = None
    _embedding_model = None

    @property
    def supabase(self):
        if self._supabase is None:
            logger.info("Initializing Supabase client for worker...")
            self._supabase = get_supabase_client()
        return self._supabase

    @property
    def gemini_flash(self):
        if self._gemini_flash is None:
            logger.info("Initializing Gemini Flash client for worker...")
            self._gemini_flash = get_gemini_flash()
        return self._gemini_flash

    @property
    def gemini_pro(self):
        if self._gemini_pro is None:
            logger.info("Initializing Gemini Pro client for worker...")
            self._gemini_pro = get_gemini_pro()
        return self._gemini_pro

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            logger.info("Initializing Embedding Model client for worker...")
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} completed successfully")
        super().on_success(retval, task_id, args, kwargs)

settings = get_settings()

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.tasks"],
    Task=EnrichmentTask  # Use our custom task class
)

celery_app.config_from_object('src.celeryconfig')
