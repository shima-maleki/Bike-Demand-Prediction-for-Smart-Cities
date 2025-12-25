"""
Logging Configuration
Centralized logging setup using loguru
"""

import sys
from pathlib import Path
from loguru import logger

from src.config.settings import get_settings

settings = get_settings()

# Remove default logger
logger.remove()

# Create logs directory
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Console logging format
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# File logging format
FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# Add console handler
logger.add(
    sys.stdout,
    format=CONSOLE_FORMAT,
    level="DEBUG" if settings.debug else "INFO",
    colorize=True,
)

# Add file handler for general logs
logger.add(
    logs_dir / "app.log",
    format=FILE_FORMAT,
    level="INFO",
    rotation="100 MB",
    retention="30 days",
    compression="zip",
)

# Add file handler for error logs
logger.add(
    logs_dir / "error.log",
    format=FILE_FORMAT,
    level="ERROR",
    rotation="50 MB",
    retention="90 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
)

# Add file handler for debug logs (only in debug mode)
if settings.debug:
    logger.add(
        logs_dir / "debug.log",
        format=FILE_FORMAT,
        level="DEBUG",
        rotation="200 MB",
        retention="7 days",
        compression="zip",
    )


def get_logger(name: str = None):
    """
    Get a logger instance with optional name

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger
