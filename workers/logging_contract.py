from __future__ import annotations

from typing import Any


WORKER_STARTED = "worker_started"
WORKER_RECONNECT = "worker_reconnect"
WORKER_ERROR = "worker_error"
WORKER_STOPPED = "worker_stopped"
WORKER_MESSAGE_RECEIVED = "worker_message_received"
WORKER_MESSAGE_PROCESSED = "worker_message_processed"


def build_worker_log_extra(
    *,
    event: str,
    worker_name: str,
    source: str,
    request_id: str | None = None,
    job_id: str | None = None,
    news_id: str | int | None = None,
    price_id: str | int | None = None,
    notification_id: str | int | None = None,
    session_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "worker_name": worker_name,
        "source": source,
    }

    if request_id:
        payload["request_id"] = request_id
    if job_id:
        payload["job_id"] = job_id
    if news_id is not None:
        payload["news_id"] = news_id
    if price_id is not None:
        payload["price_id"] = price_id
    if notification_id is not None:
        payload["notification_id"] = notification_id
    if session_id:
        payload["session_id"] = session_id
    if extra:
        payload.update(extra)

    return {
        "event": event,
        "extra": payload,
    }
