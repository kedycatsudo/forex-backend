from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def log_ingestion_event(
    *,
    level: int,
    event: str,
    provider: str | None,
    connection_id: str | None,
    state: str,
    attempt: int,
    latency_ms: int | None = None,
    error_code: str | None = None,
    error_type: str | None = None,
    message_count: int | None = None,
    **meta: Any,
) -> None:
    payload = {
        "event": event,
        "provider": provider,
        "connection_id": connection_id,
        "state": state,
        "attempt": attempt,
        "latency_ms": latency_ms,
        "error_code": error_code,
        "error_type": error_type,
        "message_count": message_count,
        "timestamp": datetime.now(UTC).isoformat(),
        "meta": meta or {},
    }
    logger.log(level, "ingestion_event", extra={"ingestion": payload})
