from __future__ import annotations

import asyncio
import contextlib
import logging
import random
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from time import monotonic
from typing import Any

from app.ingestion.config import IngestionSettings
from app.ingestion.dispatcher import MessageDispatcher
from app.ingestion.models import RawIngestionEvent
from app.ingestion.providers.base import ProviderClient
from app.ingestion.providers.errors import (
    AuthError,
    FatalConfigError,
    NetworkError,
    RateLimitError,
)
from app.ingestion.startup_check import build_ingestion_settings
from app.ingestion.supervisor_base import IngestionSupervisorLifecycle

logger = logging.getLogger(__name__)


class SupervisorState(str, Enum):
    idle = "idle"
    connecting = "connecting"
    connected = "connected"
    degraded = "degraded"
    reconnecting = "reconnecting"
    stopped = "stopped"


@dataclass
class SupervisorHealth:
    state: SupervisorState
    active_provider: str | None
    last_message_at: datetime | None
    reconnect_count: int
    failover_count: int
    reconnect_count_1h: int
    reconnect_count_24h: int
    queue_lag: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "active_provider": self.active_provider,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "reconnect_count": self.reconnect_count,
            "failover_count": self.failover_count,
            "reconnect_count_1h": self.reconnect_count_1h,
            "reconnect_count_24h": self.reconnect_count_24h,
            "queue_lag": self.queue_lag,
        }


class IngestionSupervisor(IngestionSupervisorLifecycle):
    def __init__(
        self,
        *,
        dispatcher: MessageDispatcher,
        provider_a: ProviderClient | None = None,
        provider_b: ProviderClient | None = None,
        settings: IngestionSettings | None = None,
    ) -> None:
        self._settings = settings or build_ingestion_settings()
        self._dispatcher = dispatcher
        self._provider_a = provider_a
        self._provider_b = provider_b

        self._active_provider: ProviderClient | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

        self._state = SupervisorState.idle
        self._last_message_at: datetime | None = None
        self._reconnect_count = 0
        self._failover_count = 0

        # Backoff + stable reset
        self._reconnect_attempt = 0
        self._connected_since: datetime | None = None
        self._stable_reset_seconds = 300  # 5 minutes

        # 1.1.10 health + metrics fields
        self._reconnect_events: deque[datetime] = deque()
        self._messages_total = 0
        self._messages_invalid_total = 0
        self._messages_dropped_total = 0
        self._heartbeat_misses_total = 0
        self._started_at = datetime.now(UTC)
        self._last_msg_monotonic: float | None = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            logger.info("ingestion_supervisor_start_skipped reason=already_running")
            return

        self._active_provider = self._select_active_provider()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "ingestion_supervisor_started provider=%s",
            self._active_provider.name if self._active_provider else None,
        )

    async def stop(self) -> None:
        self._stop_event.set()

        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        provider = self._active_provider
        if provider is not None:
            await provider.close()

        self._transition(SupervisorState.stopped, "manual_stop")
        logger.info("ingestion_supervisor_stopped")

    def _transition(self, to_state: SupervisorState, reason: str, **meta: Any) -> None:
        from_state = self._state
        self._state = to_state
        logger.info(
            "state_transition from=%s to=%s reason=%s meta=%s",
            from_state.value,
            to_state.value,
            reason,
            meta or {},
        )

    def _reconnects_in_window(self, seconds: int) -> int:
        now = datetime.now(UTC)
        keep_after = now - timedelta(hours=24)
        while self._reconnect_events and self._reconnect_events[0] < keep_after:
            self._reconnect_events.popleft()

        cutoff = now - timedelta(seconds=seconds)
        return sum(1 for ts in self._reconnect_events if ts >= cutoff)

    def health(self) -> dict[str, Any]:
        provider = self._active_provider
        queue_lag = None
        if hasattr(self._dispatcher, "queue_lag"):
            queue_lag = getattr(self._dispatcher, "queue_lag")

        return SupervisorHealth(
            state=self._state,
            active_provider=provider.name if provider else None,
            last_message_at=self._last_message_at,
            reconnect_count=self._reconnect_count,
            failover_count=self._failover_count,
            reconnect_count_1h=self._reconnects_in_window(3600),
            reconnect_count_24h=self._reconnects_in_window(86400),
            queue_lag=queue_lag,
        ).as_dict()

    def metrics_snapshot(self) -> dict[str, Any]:
        uptime_seconds = int((datetime.now(UTC) - self._started_at).total_seconds())
        messages_per_sec = (self._messages_total / uptime_seconds) if uptime_seconds > 0 else 0.0
        return {
            "provider": self._active_provider.name if self._active_provider else None,
            "state": self._state.value,
            "messages_total": self._messages_total,
            "messages_per_sec": messages_per_sec,
            "reconnect_attempts_total": self._reconnect_count,
            "reconnect_attempts_1h": self._reconnects_in_window(3600),
            "reconnect_attempts_24h": self._reconnects_in_window(86400),
            "dropped_messages_total": self._messages_dropped_total,
            "invalid_messages_total": self._messages_invalid_total,
            "heartbeat_misses_total": self._heartbeat_misses_total,
            "uptime_seconds": uptime_seconds,
            "last_message_at": self._last_message_at.isoformat() if self._last_message_at else None,
        }

    def _select_active_provider(self) -> ProviderClient:
        if self._settings.news_provider_a_enabled and self._provider_a:
            return self._provider_a
        if self._settings.news_provider_b_enabled and self._provider_b:
            return self._provider_b
        raise RuntimeError("No enabled provider client available for ingestion.")

    def _reconnect_decision(self, exc: Exception) -> tuple[bool, int | None, str]:
        if isinstance(exc, FatalConfigError):
            return (False, None, "fatal_config_error")
        if isinstance(exc, AuthError):
            return (False, None, "auth_error")
        if isinstance(exc, RateLimitError):
            return (True, exc.retry_after_seconds, "rate_limited")
        if isinstance(exc, NetworkError):
            return (True, None, "network_error")
        return (True, None, "unknown_error")

    def _compute_reconnect_delay(
        self,
        attempt: int,
        retry_after_seconds: int | None = None,
    ) -> float:
        base = max(1, getattr(self._settings, "reconnect_base_seconds", 1))
        max_delay = max(base, getattr(self._settings, "reconnect_max_seconds", 60))

        if retry_after_seconds is not None:
            return float(min(max_delay, max(0, retry_after_seconds)))

        delay = min(max_delay, base * (2 ** max(attempt - 1, 0)))
        jitter = random.uniform(0, 0.25)
        return float(delay + jitter)

    def _maybe_reset_reconnect_attempt(self) -> None:
        if self._connected_since is None:
            return
        healthy_for = datetime.now(UTC) - self._connected_since
        if healthy_for >= timedelta(seconds=self._stable_reset_seconds):
            if self._reconnect_attempt != 0:
                logger.info(
                    "reconnect_attempt_reset healthy_seconds=%s previous_attempt=%s",
                    int(healthy_for.total_seconds()),
                    self._reconnect_attempt,
                )
            self._reconnect_attempt = 0

    async def _run_loop(self) -> None:
        provider = self._active_provider
        if provider is None:
            raise RuntimeError("Active provider is not set.")

        while not self._stop_event.is_set():
            try:
                self._transition(SupervisorState.connecting, "startup")
                logger.info(
                    "connect_start provider=%s connection_id=%s state=%s attempt=%s "
                    "latency_ms=%s error_code=%s error_type=%s message_count=%s",
                    provider.name,
                    getattr(provider, "_connection_id", None),
                    self._state.value,
                    self._reconnect_attempt,
                    None,
                    None,
                    None,
                    None,
                )
                await provider.connect()

                self._connected_since = datetime.now(UTC)
                was_reconnecting = self._reconnect_count > 0
                logger.info(
                    "connect_ok provider=%s connection_id=%s state=%s attempt=%s "
                    "latency_ms=%s error_code=%s error_type=%s message_count=%s",
                    provider.name,
                    getattr(provider, "_connection_id", None),
                    self._state.value,
                    self._reconnect_attempt,
                    None,
                    None,
                    None,
                    None,
                )

                if was_reconnecting:
                    logger.info(
                        "reconnect_success provider=%s reconnect_count=%s",
                        provider.name,
                        self._reconnect_count,
                    )

                async for raw_payload in provider.listen():
                    self._messages_total += 1
                    self._last_msg_monotonic = monotonic()

                    logger.debug(
                        "message_received provider=%s event_id=%s",
                        provider.name,
                        raw_payload.get("id"),
                    )

                    event = self._wrap_event(raw_payload, provider)
                    ok = await self._dispatcher.dispatch(event)

                    if ok:
                        self._last_message_at = datetime.now(UTC)
                        if self._state == SupervisorState.degraded:
                            self._transition(SupervisorState.connected, "dispatch_recovered")
                        self._maybe_reset_reconnect_attempt()
                    else:
                        self._messages_invalid_total += 1
                        self._transition(SupervisorState.degraded, "dispatch_fail")
                        logger.warning(
                            "dispatch_fail provider=%s event_id=%s state=%s",
                            provider.name,
                            event.provider_event_id,
                            self._state.value,
                        )

                    # optional: pull heartbeat misses from provider if exposed
                    self._heartbeat_misses_total = int(
                        getattr(provider, "_consecutive_missed_pongs", 0)
                    )

                    if self._stop_event.is_set():
                        break

            except asyncio.CancelledError:
                raise

            except Exception as exc:
                retry, retry_after, reason = self._reconnect_decision(exc)

                logger.exception(
                    "connect_fail provider=%s reason=%s retry=%s",
                    provider.name,
                    reason,
                    retry,
                )

                if not retry:
                    self._transition(SupervisorState.stopped, reason)
                    return

                self._reconnect_count += 1
                self._reconnect_events.append(datetime.now(UTC))
                self._reconnect_attempt += 1
                self._transition(SupervisorState.reconnecting, reason)

                switched = await self._try_failover()
                if switched:
                    self._failover_count += 1
                    provider = self._active_provider
                    if provider is None:
                        raise RuntimeError("Failover switched to no provider.")

                delay_seconds = self._compute_reconnect_delay(
                    attempt=self._reconnect_attempt,
                    retry_after_seconds=retry_after,
                )
                logger.info(
                    "reconnect_scheduled provider=%s delay_seconds=%.3f "
                    "reconnect_count=%s attempt=%s reason=%s",
                    provider.name,
                    delay_seconds,
                    self._reconnect_count,
                    self._reconnect_attempt,
                    reason,
                )
                await asyncio.sleep(delay_seconds)

    async def _try_failover(self) -> bool:
        provider = self._active_provider
        if provider is None:
            return False

        is_a_active = provider is self._provider_a
        can_use_b = self._settings.news_provider_b_enabled and self._provider_b is not None

        if is_a_active and can_use_b:
            try:
                await provider.close()
            except Exception:
                logger.exception("active_provider_close_failed_during_failover")

            next_provider = self._provider_b
            if next_provider is None:
                return False

            self._active_provider = next_provider
            logger.warning("provider_failover switched_to=%s", next_provider.name)
            return True

        return False

    @staticmethod
    def _wrap_event(raw_payload: dict[str, Any], provider: ProviderClient) -> RawIngestionEvent:
        return RawIngestionEvent(
            provider_name=provider.name,
            provider_event_id=raw_payload.get("id"),
            raw_payload=raw_payload,
            transport_metadata={
                "protocol": provider.protocol,
                "channel": raw_payload.get("channel"),
                "sequence_number": raw_payload.get("sequence"),
            },
        )
