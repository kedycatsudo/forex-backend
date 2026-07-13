from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.ingestion.config import IngestionSettings
from app.ingestion.dispatcher import MessageDispatcher
from app.ingestion.models import RawIngestionEvent
from app.ingestion.providers.base import ProviderClient
from app.ingestion.providers.ws_base import HeartbeatDeadError
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "active_provider": self.active_provider,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "reconnect_count": self.reconnect_count,
            "failover_count": self.failover_count,
        }


class IngestionSupervisor(IngestionSupervisorLifecycle):
    """
    Runtime owner for ingestion lifecycle:
    - loads settings
    - chooses active provider
    - starts/stops loop
    - dispatches messages
    - tracks health
    """

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

        self._state = SupervisorState.stopped
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
    def health(self) -> dict[str, Any]:
        provider = self._active_provider
        return SupervisorHealth(
            state=self._state,
            active_provider=provider.name if provider else None,
            last_message_at=self._last_message_at,
            reconnect_count=self._reconnect_count,
            failover_count=self._failover_count,
        ).as_dict()

    def _select_active_provider(self) -> ProviderClient:
        if self._settings.news_provider_a_enabled and self._provider_a:
            return self._provider_a
        if self._settings.news_provider_b_enabled and self._provider_b:
            return self._provider_b
        raise RuntimeError("No enabled provider client available for ingestion.")

    async def _run_loop(self) -> None:
        provider = self._active_provider
        if provider is None:
            raise RuntimeError("Active provider is not set.")

        while not self._stop_event.is_set():
            try:
                self._transition(SupervisorState.connecting, "startup")
                logger.info("connect_start provider=%s state=%s", provider.name, self._state.value)

                await provider.connect()

                was_reconnecting = self._reconnect_count > 0
                self._transition(SupervisorState.connected, "connect_ok")
                logger.info("connect_ok provider=%s state=%s", provider.name, self._state.value)

                if was_reconnecting:
                    logger.info(
                        "reconnect_success provider=%s reconnect_count=%s",
                        provider.name,
                        self._reconnect_count,
                    )

                async for raw_payload in provider.listen():
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
                        logger.debug(
                            "dispatch_ok provider=%s event_id=%s",
                            provider.name,
                            event.provider_event_id,
                        )
                    else:
                        self._transition(SupervisorState.degraded, "dispatch_fail")
                        logger.warning(
                            "dispatch_fail provider=%s event_id=%s state=%s",
                            provider.name,
                            event.provider_event_id,
                            self._state.value,
                        )

                    if self._stop_event.is_set():
                        break

            except asyncio.CancelledError:
                raise

            except HeartbeatDeadError:
                self._reconnect_count += 1
                self._transition(SupervisorState.reconnecting, "heartbeat_dead")
                logger.warning(
                    "connect_fail provider=%s reason=heartbeat_dead reconnect_count=%s",
                    provider.name,
                    self._reconnect_count,
                )

                switched = await self._try_failover()
                if switched:
                    self._failover_count += 1
                    provider = self._active_provider
                    if provider is None:
                        raise RuntimeError("Failover switched to no provider.")
                    continue

                delay_seconds = 1
                logger.info(
                    "reconnect_scheduled provider=%s delay_seconds=%s reconnect_count=%s",
                    provider.name,
                    delay_seconds,
                    self._reconnect_count,
                )
                await asyncio.sleep(delay_seconds)

            except Exception:
                self._reconnect_count += 1
                self._transition(SupervisorState.reconnecting, "provider_exception")
                logger.exception(
                    "connect_fail provider=%s state=%s reconnect_count=%s",
                    provider.name,
                    self._state.value,
                    self._reconnect_count,
                )

                switched = await self._try_failover()
                if switched:
                    self._failover_count += 1
                    provider = self._active_provider
                    if provider is None:
                        raise RuntimeError("Failover switched to no provider.")
                    continue

                delay_seconds = 1
                logger.info(
                    "reconnect_scheduled provider=%s delay_seconds=%s reconnect_count=%s",
                    provider.name,
                    delay_seconds,
                    self._reconnect_count,
                )
                await asyncio.sleep(delay_seconds)

    async def _try_failover(self) -> bool:
        """
        Stub failover hook:
        if active is A and B is enabled+available, switch to B.
        """
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
            transport_metadata={"protocol": provider.protocol},
        )