from celery import Celery, Task
from src.config import Settings
from src.dependencies import get_settings
from src.logger import logger
from src.tasks import BaseTaskWithClients # Import the custom task class

settings = get_settings()

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.tasks"],
    Task=BaseTaskWithClients  # Use our custom task class
)

celery_app.config_from_object('src.celeryconfig')
