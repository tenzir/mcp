"""Shared logging configuration for build scripts."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Optional

ICON_MAP = {
    logging.DEBUG: ("·", "\033[90m"),  # grey
    logging.INFO: ("✔︎", "\033[32m"),  # green (success-style info)
    logging.WARNING: ("!", "\033[33m"),  # yellow
    logging.ERROR: ("✘", "\033[31m"),  # red
    logging.CRITICAL: ("✘", "\033[31m"),
}

RESET = "\033[0m"


class IconFormatter(logging.Formatter):
    """Formatter that prepends an icon and optional ANSI color to each message."""

    def __init__(self, use_color: Optional[bool] = None) -> None:
        super().__init__()
        if use_color is None:
            if os.environ.get("NO_COLOR"):
                use_color = False
            elif os.environ.get("FORCE_COLOR"):
                use_color = True
            else:
                use_color = True
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        icon, color = ICON_MAP.get(record.levelno, ("✔︎", "\033[32m"))
        message = record.getMessage()
        if self.use_color and color:
            icon_text = f"{color}{icon}{RESET}"
        else:
            icon_text = icon
        return f"{icon_text} {message}"


def _success(self: logging.Logger, msg: str, *args: Any, **kwargs: Any) -> None:
    self.info(msg, *args, **kwargs)


logging.Logger.success = _success  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger with icon/colored output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(IconFormatter())
        logger.addHandler(handler)
        logger.propagate = False
        logger.setLevel(logging.INFO)
    return logger
