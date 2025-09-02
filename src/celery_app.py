from celery import Celery, Task
from src.config import Settings
from src.dependencies import get_settings
from src.logger import logger

class LoggingTask(Task):
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
    include=["src.tasks"], # Points to the module where tasks will be defined
    Task=LoggingTask
)

celery_app.config_from_object('src.celeryconfig')
