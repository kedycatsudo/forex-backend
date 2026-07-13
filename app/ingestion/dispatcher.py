from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from app.ingestion.models import RawIngestionEvent

logger = logging.getLogger(__name__)


class MessageDispatcher(ABC):
    """
    Dispatcher contract:
    takes raw ingestion envelope and forwards to next stage.
    """

    @abstractmethod
    async def dispatch(self, raw_event: RawIngestionEvent) -> bool:
        """
        Returns:
            True  -> dispatch succeeded
            False -> dispatch failed (non-fatal path)
        """
        raise NotImplementedError


class InMemoryQueueDispatcher(MessageDispatcher):
    """
    Temporary dispatcher implementation for skeleton phase:
    - pushes events to an in-memory async queue
    - logs dispatch results
    """

    def __init__(self, queue: asyncio.Queue[RawIngestionEvent] | None = None) -> None:
        self._queue: asyncio.Queue[RawIngestionEvent] = queue or asyncio.Queue()

    @property
    def queue(self) -> asyncio.Queue[RawIngestionEvent]:
        return self._queue

    async def dispatch(self, raw_event: RawIngestionEvent) -> bool:
        try:
            await self._queue.put(raw_event)
            logger.debug(
                "dispatch_ok provider=%s event_id=%s queue_size=%s",
                raw_event.provider_name,
                raw_event.provider_event_id,
                self._queue.qsize(),
            )
            return True
        except Exception:
            logger.exception(
                "dispatch_fail provider=%s event_id=%s",
                raw_event.provider_name,
                raw_event.provider_event_id,
            )
            return False