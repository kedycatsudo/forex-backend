from __future__ import annotations

import asyncio
import contextlib
import logging
import random
from abc import abstractmethod
from datetime import UTC, datetime
from typing import Any, AsyncIterator

from app.ingestion.providers.base import ProviderClient
from app.ingestion.providers.errors import AuthError, NetworkError, RateLimitError

logger = logging.getLogger(__name__)


class HeartbeatDeadError(NetworkError):
    """Raised when websocket heartbeat determines the connection is dead."""


class WsProviderClient(ProviderClient):
    protocol: str = "ws"

    def __init__(
        self,
        *,
        name: str,
        url: str,
        api_key: str,
        heartbeat_interval_seconds: int = 15,
        pong_timeout_seconds: int = 5,
        missed_pongs_threshold: int = 3,
        reconnect_base_seconds: int = 1,
        reconnect_max_seconds: int = 60,
        max_retries: int = -1,
    ) -> None:
        self.name = name
        self.url = url
        self.api_key = api_key

        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.pong_timeout_seconds = pong_timeout_seconds
        self.missed_pongs_threshold = missed_pongs_threshold

        self.reconnect_base_seconds = reconnect_base_seconds
        self.reconnect_max_seconds = reconnect_max_seconds
        self.max_retries = max_retries

        self._connected = False
        self._stop_requested = False
        self._attempt = 0
        self._connection_id: str | None = None

        self._last_ping_at: datetime | None = None
        self._last_pong_at: datetime | None = None
        self._consecutive_missed_pongs = 0
        self._heartbeat_dead_events_total = 0
        self._heartbeat_misses_total = 0

    async def connect(self) -> None:
        logger.info("post_connect_transport_start provider=%s", self.name)
        await self._open_socket()
        logger.info("post_connect_transport_ok provider=%s", self.name)

        logger.info("post_connect_auth_start provider=%s", self.name)
        try:
            await self._authenticate()
        except AuthError:
            logger.exception("post_connect_auth_fail provider=%s", self.name)
            raise
        logger.info("post_connect_auth_ok provider=%s", self.name)

        logger.info("post_connect_subscribe_start provider=%s", self.name)
        try:
            await self._subscribe()
        except Exception as exc:
            logger.exception(
                "subscribe_fail provider=%s connection_id=%s error_type=%s",
                self.name,
                self._connection_id,
                exc.__class__.__name__,
            )
            raise
        logger.info("post_connect_subscribe_ok provider=%s", self.name)

        if self._supports_initial_snapshot():
            logger.info("post_connect_snapshot_start provider=%s", self.name)
            await self._request_initial_snapshot()
            logger.info("post_connect_snapshot_ok provider=%s", self.name)

        self._connected = True
        self._attempt = 0
        self._consecutive_missed_pongs = 0
        logger.info("post_connect_ready provider=%s", self.name)

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        while not self._stop_requested:
            try:
                if not self._connected:
                    await self.connect()

                heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                try:
                    logger.info("post_connect_stream_start provider=%s", self.name)
                    async for msg in self._read_messages():
                        if msg.get("type") == "pong":
                            self._last_pong_at = datetime.now(UTC)
                            self._consecutive_missed_pongs = 0
                            logger.debug("heartbeat_pong_ok provider=%s", self.name)
                            continue

                        rate_limited, retry_after = self._extract_rate_limit(msg)
                        if rate_limited:
                            logger.warning(
                                "rate_limit_detected provider=%s retry_after_seconds=%s",
                                self.name,
                                retry_after,
                            )
                            raise RateLimitError(retry_after_seconds=retry_after)

                        yield msg
                finally:
                    heartbeat_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await heartbeat_task

            except asyncio.CancelledError:
                raise
            except Exception:
                self._connected = False
                if not self._should_retry():
                    raise

                delay = self._next_backoff_seconds()
                logger.info(
                    "reconnect_scheduled provider=%s delay_seconds=%.3f attempt=%s",
                    self.name,
                    delay,
                    self._attempt,
                )
                await asyncio.sleep(delay)

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
            if not self._connected or self._stop_requested:
                break

            self._last_ping_at = datetime.now(UTC)
            logger.debug("heartbeat_ping_sent provider=%s", self.name)
            await self._send_ping()

            try:
                await asyncio.wait_for(self._await_pong(), timeout=self.pong_timeout_seconds)
                self._last_pong_at = datetime.now(UTC)
                self._consecutive_missed_pongs = 0
                logger.debug("heartbeat_pong_ok provider=%s", self.name)
            except asyncio.TimeoutError:
                self._consecutive_missed_pongs += 1
                self._heartbeat_misses_total += 1
                logger.warning(
                    "heartbeat_missed provider=%s miss_count=%s",
                    self.name,
                    self._consecutive_missed_pongs,
                )

                if self._consecutive_missed_pongs >= self.missed_pongs_threshold:
                    self._heartbeat_dead_events_total += 1
                    self._connected = False
                    logger.error(
                        "heartbeat_dead_socket_detected provider=%s miss_count=%s threshold=%s",
                        self.name,
                        self._consecutive_missed_pongs,
                        self.missed_pongs_threshold,
                    )
                    raise HeartbeatDeadError(
                        f"Missed {self.missed_pongs_threshold} consecutive pongs."
                    )

    def _supports_initial_snapshot(self) -> bool:
        return False

    async def _request_initial_snapshot(self) -> None:
        return None

    def _extract_rate_limit(self, msg: dict[str, Any]) -> tuple[bool, int | None]:
        return (False, None)

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
