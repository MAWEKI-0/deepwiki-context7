import sys
from loguru import logger

logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

# You can also configure file logging here if needed
# logger.add("file_{time}.log", rotation="500 MB")

__all__ = ["logger"]
