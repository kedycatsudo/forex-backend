import asyncio

from app.core.logging import get_logger
from workers.logging_contract import (
    WORKER_ERROR,
    WORKER_RECONNECT,
    WORKER_STARTED,
    WORKER_STOPPED,
    build_worker_log_extra,
)

WORKER_NAME = "news_worker"
SOURCE = "news_source"

logger = get_logger(__name__)


async def run_news_worker() -> None:
    reconnect_attempt = 0
    backoff_seconds = 2

    logger.info(
        "Worker started",
        extra=build_worker_log_extra(
            event=WORKER_STARTED,
            worker_name=WORKER_NAME,
            source=SOURCE,
        ),
    )

    try:
        while True:
            try:
                # Placeholder for broker read / poll / consume
                await asyncio.sleep(5)
                reconnect_attempt = 0  # reset when healthy
            except ConnectionError:
                reconnect_attempt += 1
                logger.warning(
                    "Worker reconnecting",
                    extra=build_worker_log_extra(
                        event=WORKER_RECONNECT,
                        worker_name=WORKER_NAME,
                        source=SOURCE,
                        extra_payload={
                            "reconnect_attempt": reconnect_attempt,
                            "backoff_seconds": backoff_seconds,
                        },
                    ),
                )
                await asyncio.sleep(backoff_seconds)
            except Exception:
                logger.exception(
                    "Worker unexpected loop error",
                    extra=build_worker_log_extra(
                        event=WORKER_ERROR,
                        worker_name=WORKER_NAME,
                        source=SOURCE,
                    ),
                )
                await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info(
            "Worker cancelled",
            extra=build_worker_log_extra(
                event=WORKER_STOPPED,
                worker_name=WORKER_NAME,
                source=SOURCE,
            ),
        )
        raise
    except Exception:
        logger.exception(
            "Worker crashed",
            extra=build_worker_log_extra(
                event=WORKER_ERROR,
                worker_name=WORKER_NAME,
                source=SOURCE,
            ),
        )
    finally:
        logger.info(
            "Worker stopped",
            extra=build_worker_log_extra(
                event=WORKER_STOPPED,
                worker_name=WORKER_NAME,
                source=SOURCE,
            ),
        )