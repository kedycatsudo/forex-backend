from __future__ import annotations

import asyncio

from app.core.logging import configure_logging, get_logger
from workers.news_worker import run_news_worker
from workers.notification_worker import run_notification_worker
from workers.price_worker import run_price_worker

configure_logging()
logger = get_logger(__name__)


async def main() -> None:
    logger.info("Starting worker group", extra={"event": "worker_group_started"})
    tasks = [
        asyncio.create_task(run_news_worker(), name="news_worker"),
        asyncio.create_task(run_price_worker(), name="price_worker"),
        asyncio.create_task(run_notification_worker(), name="notification_worker"),
    ]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        raise
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Worker group stopped", extra={"event": "worker_group_stopped"})


if __name__ == "__main__":
    asyncio.run(main())
