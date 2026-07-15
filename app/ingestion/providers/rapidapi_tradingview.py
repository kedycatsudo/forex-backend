from __future__ import annotations

import asyncio
import os
from collections import deque
from typing import Any, AsyncIterator
from urllib.parse import urlencode

import requests

from app.ingestion.providers.base import ProviderClient
from app.ingestion.providers.errors import NetworkError


class RapidApiTradingViewProvider(ProviderClient):
    # Keep class name for compatibility with existing wiring
    name: str = "currentsapi_latest_news"
    protocol: str = "rest_polling"

    def __init__(self, poll_seconds: float | None = None) -> None:
        raw_url = os.getenv("NEWS_PROVIDER_A_URL", "api.currentsapi.services").strip()
        self.api_key = os.getenv("NEWS_PROVIDER_A_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("NEWS_PROVIDER_A_API_KEY is required")

        if raw_url.startswith(("http://", "https://")):
            self.base_url = raw_url.rstrip("/")
        else:
            self.base_url = f"https://{raw_url.split('/', 1)[0]}"

        env_poll = os.getenv("NEWS_PROVIDER_A_POLL_SECONDS", "90").strip()
        self.poll_seconds = poll_seconds if poll_seconds is not None else float(env_poll)

        self.language = os.getenv("NEWS_PROVIDER_A_LANGUAGE", "en").strip()
        self.country = os.getenv("NEWS_PROVIDER_A_COUNTRY", "").strip()
        self.category = os.getenv("NEWS_PROVIDER_A_CATEGORY", "").strip()
        self.page_size = min(int(os.getenv("NEWS_PROVIDER_A_PAGE_SIZE", "20").strip()), 20)
        self.timeout_seconds = int(os.getenv("NEWS_PROVIDER_A_TIMEOUT_SECONDS", "20").strip())

        self._stop = False
        self._seen_ids: set[str] = set()
        self._seen_order: deque[str] = deque(maxlen=5000)

        self.headers = {
            "Authorization": self.api_key,  # use raw key unless your account requires Bearer
            "Accept": "application/json",
        }

    async def connect(self) -> None:
        self._stop = False

    def _build_url(self) -> str:
        params: dict[str, str | int] = {
            "language": self.language or "en",
            "page_size": self.page_size,
        }
        if self.country:
            params["country"] = self.country
        if self.category:
            params["category"] = self.category

        return f"{self.base_url}/v1/latest-news?{urlencode(params)}"

    def _remember_id(self, item_id: str) -> None:
        if item_id in self._seen_ids:
            return
        if len(self._seen_order) == self._seen_order.maxlen:
            oldest = self._seen_order[0]
            self._seen_ids.discard(oldest)
        self._seen_order.append(item_id)
        self._seen_ids.add(item_id)

    def listen(self) -> AsyncIterator[dict[str, Any]]:
        async def _stream() -> AsyncIterator[dict[str, Any]]:
            while not self._stop:
                try:
                    r = requests.get(
                        self._build_url(),
                        headers=self.headers,
                        timeout=self.timeout_seconds,
                    )
                    if r.status_code >= 400:
                        print(
                            f"currents status={r.status_code} body={r.text[:500]}",
                            flush=True,
                        )
                    r.raise_for_status()
                    payload = r.json()
                except requests.RequestException as exc:
                    raise NetworkError(str(exc)) from exc

                if isinstance(payload, dict):
                    items = payload.get("news") or []
                elif isinstance(payload, list):
                    items = payload
                else:
                    items = []

                print(f"currentsapi poll items_count={len(items)}", flush=True)

                new_count = 0
                for n in items:
                    item_id = str(n.get("id") or "").strip()
                    if not item_id or item_id in self._seen_ids:
                        continue

                    self._remember_id(item_id)
                    new_count += 1

                    print(
                        "currentsapi new_item "
                        f"id={item_id} "
                        f"title={n.get('title') or ''} "
                        f"published={n.get('published') or ''}",
                        flush=True,
                    )

                    yield {
                        "id": item_id,
                        "channel": "forex_news",
                        "sequence": None,
                        "headline": n.get("title") or "",
                        "summary": n.get("description") or "",
                        "symbol": "FX",
                        "time": n.get("published"),
                        "source": "currentsapi",
                        "url": n.get("url"),
                        "author": n.get("author"),
                        "image": n.get("image"),
                        "language": n.get("language"),
                        "category": n.get("category") or [],
                        "raw": n,
                    }

                print(f"currentsapi poll new_items={new_count}", flush=True)
                await asyncio.sleep(self.poll_seconds)

        return _stream()

    async def close(self) -> None:
        self._stop = True
