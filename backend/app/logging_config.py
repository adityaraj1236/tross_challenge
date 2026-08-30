from __future__ import annotations

import logging
import sys
from typing import Any, Mapping

# Never let these show up in logs, even if a caller passes them by mistake.
_REDACT_KEYS = {
    "cookie", "cookies", "authorization", "auth", "li_at", "jsessionid",
    "csrf-token", "csrf_token", "set-cookie", "session", "password",
}


def _redact(context: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in context.items():
        redacted[key] = "***REDACTED***" if key.lower() in _REDACT_KEYS else value
    return redacted


class _ContextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        context = getattr(record, "context", None)
        if context:
            base = f"{base} | context={_redact(context)}"
        return base


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _ContextFormatter(fmt="%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Quiet noisy third-party loggers unless we're actually debugging them.
    logging.getLogger("httpx").setLevel(max(logging.WARNING, root.level))
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    context: Mapping[str, Any] | None = None,
) -> None:
    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        message,
        extra={"context": _redact(context or {})},
    )
