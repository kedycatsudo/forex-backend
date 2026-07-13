from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.ingestion.supervisor import SupervisorState


@dataclass(frozen=True)
class IngestionHealthSnapshot:
    active_provider: str | None
    state: SupervisorState
    last_message_at: datetime | None
    reconnect_count: int
    failover_count: int

    def as_dict(self) -> dict[str, str | int | None]:
        return {
            "active_provider": self.active_provider,
            "state": self.state.value,
            "last_message_at": (
                self.last_message_at.isoformat() if self.last_message_at else None
            ),
            "reconnect_count": self.reconnect_count,
            "failover_count": self.failover_count,
        }