from celery import Celery, Task
from src.config import Settings
from src.dependencies import get_settings
from src.logger import logger

settings = get_settings()

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.tasks"],
)

# Import the custom task class after celery_app is defined to avoid circular import
from src.celery_base import BaseTaskWithClients
celery_app.Task = BaseTaskWithClients  # Assign our custom task class

celery_app.config_from_object('src.celeryconfig')
