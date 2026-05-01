"""
logging_config.py — Structured logging setup.

Creates two handlers:
  1. File handler  → logs/trading_bot.log  (DEBUG+, JSON-friendly format)
  2. Console handler → stderr              (INFO+, human-friendly format)
"""

import logging
import logging.handlers
import os
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

_CONFIGURED = False


def setup_logging(level: str = "DEBUG") -> None:
    """
    Configure root logger.  Safe to call multiple times (idempotent).

    Args:
        level: Minimum log level for the file handler ('DEBUG', 'INFO', etc.)
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, level.upper(), logging.DEBUG)

    root = logging.getLogger("trading_bot")
    root.setLevel(logging.DEBUG)  # capture everything; handlers filter

    # ------------------------------------------------------------------
    # File handler — rotating, max 5 MB × 3 files
    # ------------------------------------------------------------------
    # File handler captures DEBUG+ to disk for post-mortem and audit.
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(file_fmt)

    # ------------------------------------------------------------------
    # Console handler — colourised, INFO and above
    # ------------------------------------------------------------------
    # Console output is human-friendly with coloured level names.
    console_fmt = _ColouredFormatter(
        fmt="%(asctime)s  %(levelname_coloured)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_fmt)

    root.addHandler(file_handler)
    root.addHandler(console_handler)


# ---------------------------------------------------------------------------
# ANSI colour helper
# ---------------------------------------------------------------------------

_COLOURS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}
_RESET = "\033[0m"


class _ColouredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        colour = _COLOURS.get(record.levelname, "")
        record.levelname_coloured = f"{colour}{record.levelname:<8}{_RESET}"
        return super().format(record)

# Small helper to inject ANSI colours into the level label for console logs.
