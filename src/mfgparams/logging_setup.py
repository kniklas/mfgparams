"""Stdlib logging configuration (Constitution VIII).

Application/diagnostic log messages are always written in English,
independent of the active user-facing locale (FR-019f) — this module and
every ``logging.getLogger(...)`` call elsewhere in the codebase MUST use
hard-coded English strings, never message-catalog lookups.
"""

from __future__ import annotations

import logging

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

_configured = False


def configure_logging(level: int = logging.WARNING) -> None:
    """Configure the root logger with a plain English format, once.

    Idempotent: subsequent calls only adjust the level, without adding
    duplicate handlers.
    """

    global _configured

    root = logging.getLogger()
    if not _configured:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(handler)
        _configured = True

    root.setLevel(level)
