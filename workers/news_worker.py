from __future__ import annotations

import asyncio
import signal
from typing import cast

from app.core.logging import configure_logging, get_logger
from app.ingestion.dispatcher import IngestionMessageDispatcher
from app.ingestion.providers.base import ProviderClient
from app.ingestion.providers.rapidapi_tradingview import RapidApiTradingViewProvider
from app.ingestion.supervisor import IngestionSupervisor
from workers.logging_contract import (
    WORKER_ERROR,
    WORKER_STARTED,
    WORKER_STOPPED,
    build_worker_log_extra,
)

WORKER_NAME = "news_worker"
SOURCE = "ingestion_supervisor"
configure_logging()
logger = get_logger(__name__)
provider_a = cast(ProviderClient, RapidApiTradingViewProvider())


async def run_news_worker() -> None:
    """
    Production news worker runtime:
    - starts ingestion supervisor
    - blocks until cancelled/signal
    - graceful stop with timeout
    """
    dispatcher = IngestionMessageDispatcher()
    supervisor = IngestionSupervisor(dispatcher=dispatcher, provider_a=provider_a)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    print("news_worker entered run_news_worker", flush=True)

    def _request_stop() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # Windows fallback; cancellation path still works
            pass

    logger.info(
        "Worker started",
        extra=build_worker_log_extra(
            event=WORKER_STARTED,
            worker_name=WORKER_NAME,
            source=SOURCE,
        ),
    )

    try:
        await supervisor.start()
        await stop_event.wait()
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
            "Worker unexpected loop error",
            extra=build_worker_log_extra(
                event=WORKER_ERROR,
                worker_name=WORKER_NAME,
                source=SOURCE,
            ),
        )
        raise
    finally:
        try:
            await asyncio.wait_for(supervisor.stop(), timeout=30)
        except TimeoutError:
            logger.exception(
                "Worker graceful shutdown timeout",
                extra=build_worker_log_extra(
                    event=WORKER_ERROR,
                    worker_name=WORKER_NAME,
                    source=SOURCE,
                    extra={"shutdown_timeout_seconds": 30},
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


if __name__ == "__main__":
    configure_logging()
    asyncio.run(run_news_worker())
