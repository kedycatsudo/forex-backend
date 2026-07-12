from typing import Any, TypedDict


class WorkerMessage(TypedDict, total=False):
    request_id: str
    source: str
    session_id: str

    news_id: str | int
    price_id: str | int
    notification_id: str | int

    payload: dict[str, Any]
