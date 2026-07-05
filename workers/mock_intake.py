import itertools
from typing import Any


_MESSAGES = itertools.cycle(
    [
        # News-like message (with API trace)
        {
            "request_id": "req-news-123",
            "news_id": 42,
            "source": "news_source",
            "payload": {"title": "EUR/USD up"},
        },
        # Price-like message (no request_id -> should generate job_id)
        {
            "price_id": "px-1001",
            "symbol": "EURUSD",
            "source": "price_source",
            "payload": {"bid": 1.0821, "ask": 1.0823},
        },
        # Notification-like message
        {
            "request_id": "req-notif-456",
            "notification_id": "notif-9001",
            "session_id": "sess-1",
            "source": "notification_source",
            "payload": {"user_id": "u1", "text": "Price alert triggered"},
        },
    ]
)


def get_next_mock_message() -> dict[str, Any]:
    return next(_MESSAGES)