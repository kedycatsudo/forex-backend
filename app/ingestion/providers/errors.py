from __future__ import annotations

from dataclasses import dataclass


class ProviderError(Exception):
    pass


class AuthError(ProviderError):
    pass


class NetworkError(ProviderError):
    pass


@dataclass
class RateLimitError(ProviderError):
    retry_after_seconds: int | None = None


class FatalConfigError(ProviderError):
    pass
