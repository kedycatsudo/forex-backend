from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class ProviderClient(ABC):
    """
    Provider client contract.
    Concrete providers (ws/http) must implement lifecycle + stream reading.
    """

    name: str 
    protocol: str

    @abstractmethod
    async def connect(self) -> None:
        """Establish provider connection/session."""
        raise NotImplementedError

    @abstractmethod
    def listen(self) -> AsyncIterator[dict[str, Any]]:
        """
        Yield raw provider messages/events as dict payloads.
        Long-running async stream for ws or polling loop.
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Gracefully close provider resources."""
        raise NotImplementedError