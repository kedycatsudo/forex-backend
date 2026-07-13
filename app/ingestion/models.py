from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RawIngestionEvent(BaseModel):
    """
    Canonical raw envelope before normalization.
    """

    provider_name: str = Field(..., description="Logical provider name, e.g. TradingEconomics")
    provider_event_id: str | None = Field(
        default=None, description="Provider-native event/message id if available"
    )
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when ingestion received the event",
    )
    raw_payload: dict[str, Any] = Field(
        ..., description="Original provider payload (un-normalized)"
    )
    transport_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Transport context (protocol, channel, sequence, headers, cursor, etc)",
    )

    @field_validator("received_at")
    @classmethod
    def ensure_received_at_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
