from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvName = Literal["local", "staging", "prod"]

BASE_DIR = Path(__file__).resolve().parents[2]  # project root
ENV_FILE = BASE_DIR / ".env"


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core environment
    ENV: EnvName = "local"

    # Internal/private endpoint auth
    INTERNAL_API_KEY: str = Field(default="", min_length=0)

    # CORS
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Rate limits
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_RPM_PUBLIC: int = 60

    # Docs exposure
    DOCS_ENABLED: bool = True

    # Reverse proxy trust list (comma-separated CIDRs/IPs)
    TRUSTED_PROXY_CIDRS: str = "127.0.0.1/32"

    @field_validator("DOCS_ENABLED")
    @classmethod
    def _force_docs_off_in_prod(cls, v: bool, info):
        env = info.data.get("ENV", "local")
        if env == "prod":
            return False
        return v

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def trusted_proxy_cidrs_list(self) -> list[str]:
        return [c.strip() for c in self.TRUSTED_PROXY_CIDRS.split(",") if c.strip()]


@lru_cache
def get_security_settings() -> SecuritySettings:
    return SecuritySettings()