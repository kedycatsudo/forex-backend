import asyncio
from typing import Any

from app.core.logging import get_logger
from workers.correlation import bind_correlation
from workers.logging_contract import (
    WORKER_ERROR,
    WORKER_MESSAGE_PROCESSED,
    WORKER_MESSAGE_RECEIVED,
    WORKER_RECONNECT,
    WORKER_STARTED,
    WORKER_STOPPED,
    build_worker_log_extra,
)
from workers.mock_intake import get_next_mock_message

WORKER_NAME = "price_worker"
SOURCE = "price_source"

logger = get_logger(__name__)


async def _process_price_message(message: dict[str, Any]) -> None:
    await asyncio.sleep(0.2)
    # raise ValueError("simulated price processing failure")


async def run_price_worker() -> None:
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
                message = get_next_mock_message()

                incoming_request_id = message.get("request_id")
                price_id = message.get("price_id")
                session_id = message.get("session_id")

                with bind_correlation(incoming_request_id) as corr:
                    try:
                        logger.info(
                            "Worker message received",
                            extra=build_worker_log_extra(
                                event=WORKER_MESSAGE_RECEIVED,
                                worker_name=WORKER_NAME,
                                source=SOURCE,
                                request_id=corr["request_id"],
                                job_id=corr["job_id"],
                                price_id=price_id,
                                session_id=session_id,
                            ),
                        )

                        await _process_price_message(message)

                        logger.info(
                            "Worker message processed",
                            extra=build_worker_log_extra(
                                event=WORKER_MESSAGE_PROCESSED,
                                worker_name=WORKER_NAME,
                                source=SOURCE,
                                request_id=corr["request_id"],
                                job_id=corr["job_id"],
                                price_id=price_id,
                                session_id=session_id,
                            ),
                        )

                    except Exception:
                        logger.exception(
                            "Worker message processing failed",
                            extra=build_worker_log_extra(
                                event=WORKER_ERROR,
                                worker_name=WORKER_NAME,
                                source=SOURCE,
                                request_id=corr["request_id"],
                                job_id=corr["job_id"],
                                price_id=price_id,
                                session_id=session_id,
                            ),
                        )

                reconnect_attempt = 0
                await asyncio.sleep(1)

            except ConnectionResetError:
                reconnect_attempt += 1
                logger.warning(
                    "Worker reconnecting",
                    extra=build_worker_log_extra(
                        event=WORKER_RECONNECT,
                        worker_name=WORKER_NAME,
                        source=SOURCE,
                        extra={
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

    finally:
        logger.info(
            "Worker stopped",
            extra=build_worker_log_extra(
                event=WORKER_STOPPED,
                worker_name=WORKER_NAME,
                source=SOURCE,
            ),
        )