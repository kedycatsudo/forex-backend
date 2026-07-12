from .base import NewsProviderClient


class ProviderBClient(NewsProviderClient):
    name = "SecondaryCalendarProvider"
    protocol = "http"

    async def connect(self) -> None:
        return None

    async def listen(self):
        if False:
            yield {}
        return

    async def close(self) -> None:
        return None