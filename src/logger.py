import sys
from loguru import logger
from src.config import Settings

def configure_logging(settings: Settings):
    """
    Configures the application's logger based on the provided settings.

    This function removes the default Loguru handler and sets up new handlers
    for console and optional file logging, adhering to production best practices.

    Args:
        settings: The application settings object.
    """
    logger.remove()

    # Console Sink
    # Use JSON format in production, otherwise use a human-readable format.
    if settings.LOG_JSON_FORMAT:
        logger.add(
            sys.stdout,
            level=settings.LOG_LEVEL.upper(),
            serialize=True,
            enqueue=True,  # Make logging non-blocking and process-safe
            diagnose=False, # Do not leak sensitive data in production
        )
    else:
        logger.add(
            sys.stdout,
            level=settings.LOG_LEVEL.upper(),
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=True,
            enqueue=True,
        )

    # File Sink (optional)
    # In a production environment, it's crucial to log to a file.
    if settings.LOG_FILE:
        logger.add(
            settings.LOG_FILE,
            level=settings.LOG_LEVEL.upper(),
            serialize=True,      # Always serialize file logs for machine readability
            rotation="10 MB",    # Rotate files when they reach 10 MB
            retention="7 days",  # Keep logs for 7 days
            compression="zip",   # Compress old log files
            enqueue=True,        # Make logging non-blocking and process-safe
            diagnose=False,      # Do not leak sensitive data in production
        )

# Instantiate settings and configure logging on import
settings = Settings()
configure_logging(settings)

__all__ = ["logger"]
