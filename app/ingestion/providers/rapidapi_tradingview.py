from __future__ import annotations

import asyncio
import os
from typing import Any, AsyncIterator

import requests

from app.ingestion.providers.base import ProviderClient
from app.ingestion.providers.errors import NetworkError


class RapidApiTradingViewProvider(ProviderClient):
    name: str = "rapidapi_tradingview"
    protocol: str = "rest_polling"

    def __init__(self, poll_seconds: float = 30.0) -> None:
        self.host = os.getenv("NEWS_PROVIDER_A_URL", "tradingview-api1.p.rapidapi.com")
        self.key = os.getenv("NEWS_PROVIDER_A_API_KEY", "")
        if not self.key:
            raise ValueError("NEWS_PROVIDER_A_API_KEY is required")

        self.base_url = f"https://{self.host}"
        self.poll_seconds = poll_seconds
        self._stop = False
        self.headers = {
            "x-rapidapi-key": self.key,
            "x-rapidapi-host": self.host,
            "Content-Type": "application/json",
        }

    async def connect(self) -> None:
        self._stop = False

    def listen(self) -> AsyncIterator[dict[str, Any]]:
        async def _stream() -> AsyncIterator[dict[str, Any]]:
            while not self._stop:
                try:
                    r = requests.get(
                        f"{self.base_url}/api/news/forex",
                        headers=self.headers,
                        timeout=20,
                    )
                    r.raise_for_status()
                    payload = r.json()
                except requests.RequestException as exc:
                    raise NetworkError(str(exc)) from exc

                items = payload if isinstance(payload, list) else payload.get("data", [])
                for n in items:
                    yield {
                        "id": str(n.get("id") or n.get("story_id") or ""),
                        "channel": "forex_news",
                        "sequence": None,
                        "headline": n.get("title") or n.get("headline") or "",
                        "summary": n.get("description") or "",
                        "symbol": n.get("symbol") or "FX",
                        "time": n.get("published_at") or n.get("time"),
                        "source": n.get("source") or "tradingview-rapidapi",
                        "raw": n,
                    }

                await asyncio.sleep(self.poll_seconds)

        return _stream()

    async def close(self) -> None:
        self._stop = True