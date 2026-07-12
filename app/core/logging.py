import json
import logging
import os
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# Shared context var(set by middleware)
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

SERVICE_NAME = os.getenv("APP_Name", "forex-backend")
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO".upper())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "env": APP_ENV,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "event": getattr(record, "event", None),
        }

        # Optional structured extras
        extra = getattr(record, "extra", None)
        if extra is not None:
            payload["extra"] = extra

        # Exception stack if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Remove None values for cleaner logs
        payload = {k: v for k, v in payload.items() if v is not None}
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Reset existing handlers (important for reload/dev)

    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
