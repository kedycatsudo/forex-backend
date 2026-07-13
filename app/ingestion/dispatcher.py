from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MessageDispatcher(ABC):
    """
    Dispatcher contract.
    Accepts raw ingestion events and passes them to the next stage.
    """

    @abstractmethod
    async def dispatch(self, raw_event: dict[str, Any]) -> None:
        raise NotImplementedError