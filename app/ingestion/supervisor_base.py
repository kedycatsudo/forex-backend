from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IngestionSupervisorLifecycle(ABC):
    """
    Supervisor lifecycle contract.
    """

    @abstractmethod
    async def start(self) -> None:
        """Start ingestion runtime."""
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        """Stop ingestion runtime gracefully."""
        raise NotImplementedError

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return current ingestion health snapshot."""
        raise NotImplementedError