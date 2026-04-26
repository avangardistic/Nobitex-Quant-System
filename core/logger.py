"""Logging helpers.

Limitations:
- Uses standard library logging only and does not rotate logs automatically.
"""

import logging
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger that writes to stdout and logs/app.log."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    Path("logs").mkdir(exist_ok=True)
    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
