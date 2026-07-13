from __future__ import annotations

import asyncio
from abc import abstractmethod
from datetime import UTC, datetime
from typing import Any, AsyncIterator

from app.ingestion.providers.base import ProviderClient


class HttpPollingProviderClient(ProviderClient):
    """
    Reusable HTTP polling provider base:
    - periodic fetch loop
    - cursor/last_seen hooks
    """

    protocol: str = "http"

    def __init__(
        self,
        *,
        name: str,
        url: str,
        api_key: str,
        poll_interval_seconds: int = 15,
        timeout_seconds: int = 20,
    ) -> None:
        self.name = name
        self.url = url
        self.api_key = api_key
        self.poll_interval_seconds = poll_interval_seconds
        self.timeout_seconds = timeout_seconds

        self._stop_requested = False
        self._connected = False
        self._cursor: str | None = None
        self._last_seen_at: datetime | None = None

    async def connect(self) -> None:
        await self._open_session()
        self._connected = True

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        if not self._connected:
            await self.connect()

        while not self._stop_requested:
            events = await self._fetch_batch(cursor=self._cursor, last_seen_at=self._last_seen_at)

            for event in events:
                self._last_seen_at = datetime.now(UTC)
                yield event

            self._cursor = self._next_cursor(events, self._cursor)
            await asyncio.sleep(self.poll_interval_seconds)

    async def close(self) -> None:
        self._stop_requested = True
        self._connected = False
        await self._close_session()

    # ---- hooks for concrete providers ----
    @abstractmethod
    async def _open_session(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _fetch_batch(
        self, *, cursor: str | None, last_seen_at: datetime | None
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def _next_cursor(
        self, events: list[dict[str, Any]], current_cursor: str | None
    ) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def _close_session(self) -> None:
        raise NotImplementedError