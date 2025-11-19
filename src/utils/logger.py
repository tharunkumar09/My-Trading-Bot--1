from __future__ import annotations

import logging
import logging.config
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def configure_logging(level: str = "INFO") -> None:
    """Initialise a rotating file + console logger."""

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "standard",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": level,
                "formatter": "standard",
                "filename": LOG_DIR / "trading_bot.log",
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 5,
            },
        },
        "root": {"handlers": ["console", "file"], "level": level},
    }

    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    if not logging.getLogger().handlers:
        configure_logging()
    return logging.getLogger(name)
