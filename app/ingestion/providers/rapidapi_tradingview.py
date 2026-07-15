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

    def __init__(self, poll_seconds: float | None = None) -> None:
        raw_url = os.getenv("NEWS_PROVIDER_A_URL", "tradingview-api1.p.rapidapi.com").strip()
        self.key = os.getenv("NEWS_PROVIDER_A_API_KEY", "").strip()
        if not self.key:
            raise ValueError("NEWS_PROVIDER_A_API_KEY is required")

        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            self.base_url = raw_url.rstrip("/")
            self.host = raw_url.split("://", 1)[1].split("/", 1)[0]
        else:
            self.host = raw_url.split("/", 1)[0]
            self.base_url = f"https://{self.host}"

        env_poll = os.getenv("NEWS_PROVIDER_A_POLL_SECONDS", "30").strip()
        self.poll_seconds = poll_seconds if poll_seconds is not None else float(env_poll)

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
                    print(
                        f"status={r.status_code} payload_type={type(payload).__name__}", flush=True
                    )
                    if isinstance(payload, list):
                        items = payload
                    elif isinstance(payload, dict):
                        items = (
                            payload.get("items")
                            or payload.get("data")
                            or payload.get("result")
                            or payload.get("news")
                            or []
                        )
                    else:
                        items = []

                    print(f"rapidapi poll items_count={len(items)}", flush=True)
                    for n in items[:3]:
                        print(
                            f"id={n.get('id')} title={n.get('title')} time={n.get('published_at')}",
                            flush=True,
                        )
                except requests.RequestException as exc:
                    raise NetworkError(str(exc)) from exc

                items = payload if isinstance(payload, list) else payload.get("data", [])

                for n in items:
                    print(
                        f"rapidapi item id={n.get('id') or n.get('story_id')} title={n.get('title')}",  # noqa: E501
                        flush=True,
                    )
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
