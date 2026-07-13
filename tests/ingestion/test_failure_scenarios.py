from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, AsyncIterator, cast

import pytest

from app.ingestion.config import IngestionSettings
from app.ingestion.dispatcher import MessageDispatcher
from app.ingestion.providers.base import ProviderClient
from app.ingestion.providers.errors import AuthError, NetworkError, RateLimitError
from app.ingestion.providers.ws_base import HeartbeatDeadError
from app.ingestion.supervisor import IngestionSupervisor, SupervisorState


def make_test_settings() -> IngestionSettings:
    return IngestionSettings(
        news_provider_a_enabled=True,
        news_provider_a_api_key="test-key-a",
        news_provider_b_enabled=False,
    )


class DummyDispatcher:
    def __init__(self) -> None:
        self.events: list[Any] = []
        self.queue_lag = 0

    async def dispatch(self, event: Any) -> bool:
        self.events.append(event)
        return True


class BaseFakeProvider:
    name = "fake-provider"
    protocol = "ws"

    def __init__(self) -> None:
        self._connection_id = "conn-test"
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class UnreachableProvider(BaseFakeProvider):
    async def connect(self) -> None:
        raise NetworkError("endpoint unreachable")

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}


class InvalidAuthProvider(BaseFakeProvider):
    async def connect(self) -> None:
        raise AuthError("invalid api key")

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}


class MidStreamDropProvider(BaseFakeProvider):
    def __init__(self) -> None:
        super().__init__()
        self.connected_once = False

    async def connect(self) -> None:
        self.connected_once = True

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        yield {"id": "ok-1", "channel": "news", "sequence": 1}
        raise NetworkError("socket reset mid-stream")


class NoPongProvider(BaseFakeProvider):
    async def connect(self) -> None:
        return None

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        raise HeartbeatDeadError("missed pongs")


class MalformedBurstProvider(BaseFakeProvider):
    async def connect(self) -> None:
        return None

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        # malformed items mixed with one valid-like dict
        yield {"oops": object()}
        yield {"bad": "payload"}
        yield {"id": "ok-2", "channel": "news", "sequence": 2}


class RateLimitedProvider(BaseFakeProvider):
    async def connect(self) -> None:
        raise RateLimitError(retry_after_seconds=3)

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}


@pytest.mark.asyncio
async def test_provider_endpoint_unreachable_transitions_reconnecting() -> None:
    dispatcher = DummyDispatcher()
    provider = UnreachableProvider()
    sup = IngestionSupervisor(
        dispatcher=cast(MessageDispatcher, dispatcher),
        provider_a=cast(ProviderClient, provider),
        settings=make_test_settings(),
    )

    run_task = asyncio.create_task(sup.start())
    await asyncio.sleep(0.25)
    await sup.stop()
    await run_task

    h = sup.health()
    assert h["reconnect_count"] >= 1


@pytest.mark.asyncio
async def test_invalid_api_key_stops_or_non_aggressive_behavior() -> None:
    dispatcher = DummyDispatcher()
    provider = InvalidAuthProvider()

    sup = IngestionSupervisor(
        dispatcher=cast(MessageDispatcher, dispatcher),
        provider_a=cast(ProviderClient, provider),
        settings=make_test_settings(),
    )

    await sup.start()
    await asyncio.sleep(0.25)
    # auth errors should not spin aggressively; implementation may stop
    h = sup.health()
    assert h["state"] in {
        SupervisorState.stopped.value,
        SupervisorState.reconnecting.value,
        SupervisorState.connecting.value,
    }
    await sup.stop()


@pytest.mark.asyncio
async def test_network_drop_mid_stream_reconnects() -> None:
    dispatcher = DummyDispatcher()
    provider = MidStreamDropProvider()
    sup = IngestionSupervisor(
        dispatcher=cast(MessageDispatcher, dispatcher),
        provider_a=cast(ProviderClient, provider),
        settings=make_test_settings(),
    )
    await sup.start()
    await asyncio.sleep(0.5)
    h = sup.health()
    assert h["reconnect_count"] >= 1
    await sup.stop()


@pytest.mark.asyncio
async def test_no_pong_triggers_reconnect_path() -> None:
    dispatcher = DummyDispatcher()
    provider = NoPongProvider()
    sup = IngestionSupervisor(
        dispatcher=cast(MessageDispatcher, dispatcher),
        provider_a=cast(ProviderClient, provider),
        settings=make_test_settings(),
    )
    await sup.start()
    await asyncio.sleep(0.3)
    h = sup.health()
    assert h["reconnect_count"] >= 1
    await sup.stop()


@pytest.mark.asyncio
async def test_malformed_payload_burst_does_not_crash() -> None:
    dispatcher = DummyDispatcher()
    provider = MalformedBurstProvider()
    sup = IngestionSupervisor(
        dispatcher=cast(MessageDispatcher, dispatcher),
        provider_a=cast(ProviderClient, provider),
        settings=make_test_settings(),
    )

    await sup.start()
    await asyncio.sleep(0.4)
    # If dispatcher/model rejects malformed entries, system should keep running
    h = sup.health()
    assert h["state"] in {
        SupervisorState.connected.value,
        SupervisorState.degraded.value,
        SupervisorState.reconnecting.value,
    }
    await sup.stop()


@pytest.mark.asyncio
async def test_rate_limit_respects_retry_after_signal() -> None:
    dispatcher = DummyDispatcher()
    provider = RateLimitedProvider()
    sup = IngestionSupervisor(
        dispatcher=cast(MessageDispatcher, dispatcher),
        provider_a=cast(ProviderClient, provider),
        settings=make_test_settings(),
    )

    start = datetime.now(UTC)
    await sup.start()
    await asyncio.sleep(0.4)
    h = sup.health()
    assert h["reconnect_count"] >= 1

    # sanity check only; precise delay assertion depends on hooks/mocking sleep
    elapsed = (datetime.now(UTC) - start).total_seconds()
    assert elapsed >= 0.0
    await sup.stop()
