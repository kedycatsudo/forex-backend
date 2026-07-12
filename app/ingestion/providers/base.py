from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class NewsProviderClient(ABC):
    name: str
    protocol: str

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...