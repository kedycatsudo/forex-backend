from __future__ import annotations
import contextlib
import asyncio
import random
from abc import abstractmethod
from typing import Any, AsyncIterator

from app.ingestion.providers.base import ProviderClient


class WsProviderClient(ProviderClient):
    """
    Reusable WebSocket provider base:
    - connection lifecycle
    - heartbeat loop hooks
    - reconnect with exponential backoff + jitter
    """

    protocol: str = "ws"

    def __init__(
        self,
        *,
        name: str,
        url: str,
        api_key: str,
        heartbeat_interval_seconds: int = 30,
        reconnect_base_seconds: int = 1,
        reconnect_max_seconds: int = 60,
        max_retries: int = -1,  # -1 => infinite
    ) -> None:
        self.name = name
        self.url = url
        self.api_key = api_key
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.reconnect_base_seconds = reconnect_base_seconds
        self.reconnect_max_seconds = reconnect_max_seconds
        self.max_retries = max_retries

        self._connected = False
        self._stop_requested = False
        self._attempt = 0
        self._connection_id = None

    async def connect(self) -> None:
        await self._open_socket()
        await self._authenticate()
        await self._subscribe()
        self._connected = True
        self._attempt = 0

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        while not self._stop_requested:
            try:
                if not self._connected:
                    await self.connect()

                heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                try:
                    async for msg in self._read_messages():
                        yield msg
                finally:
                    heartbeat_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await heartbeat_task

            except Exception:
                self._connected = False
                if not self._should_retry():
                    raise
                await asyncio.sleep(self._next_backoff_seconds())

    async def close(self) -> None:
        self._stop_requested = True
        self._connected = False
        await self._close_socket()

    def _should_retry(self) -> bool:
        if self.max_retries == -1:
            return True
        return self._attempt < self.max_retries

    def _next_backoff_seconds(self) -> float:
        self._attempt += 1
        delay = min(
            self.reconnect_max_seconds,
            self.reconnect_base_seconds * (2 ** max(self._attempt - 1, 0)),
        )
        jitter = random.uniform(0, 0.25)
        return delay + jitter

    async def _heartbeat_loop(self) -> None:
        while self._connected and not self._stop_requested:
            await asyncio.sleep(self.heartbeat_interval_seconds)
            await self._send_ping()
            await self._await_pong()

    # ---- hooks for concrete providers ----
    @abstractmethod
    async def _open_socket(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _authenticate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _subscribe(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _read_messages(self) -> AsyncIterator[dict[str, Any]]:
        raise NotImplementedError


    @abstractmethod
    async def _send_ping(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _await_pong(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _close_socket(self) -> None:
        raise NotImplementedError