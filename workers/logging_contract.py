from __future__ import annotations

from typing import Any

# Standart worker lifecycle \ proccessing events

WORKER_STARTED = "worker_started"
WORKER_RECONNECT = "worker_reconnect"
WORKER_ERROR= "worker_error"
WORKER_STOPPED= "worker_stopped"
WORKER_MESSAGE_RECEIVED= "worker_message_recieved"
WORKER_MESSAGE_PROCESSED="worker_message_processed"


def build_worker_log_extra(
    *,
    event:str,
    worker_name:str,
    source:str,
    request_id:str |None=None,
    job_id:str |None=None,
    news_id:str | int | None=None,
    session_id:str |None=None,
    extra_payload: dict[str,Any] | None=None,
) -> dict[str,Any]:
    
    """
        Build a consistent structured `extra` payload for logger calls.

        Usage:
            logger.info(
                "Worker started",
                extra=build_worker_log_extra(
                    event=WORKER_STARTED,
                    worker_name="news_worker",
                    source="redis_stream:news",
                ),
            )
        """
    payload: dict[str,Any]={
        "worker_name":worker_name,
        "source":source,
    }

    if request_id:
        payload["request_id"]=request_id
    if job_id:
        payload["job_id"] = job_id
    if news_id is not None:
        payload["news_id"] = session_id
    if extra_payload:
        payload.update(extra_payload)
 
    return{
        "event":event,
        "extra_payload":payload,
    }