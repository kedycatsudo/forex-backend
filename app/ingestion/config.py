from enum import Enum

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderProtocol(str, Enum):
    ws = "ws"
    http = "http"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class IngestionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Provider A
    news_provider_a_enabled: bool = True
    news_provider_a_name: str = "TradingEconomics"
    news_provider_a_protocol: ProviderProtocol = ProviderProtocol.http
    news_provider_a_url: str = ""
    news_provider_a_api_key: str = ""
    news_provider_a_timeout_seconds: int = 15
    news_provider_a_heartbeat_interval_seconds: int = 30
    news_provider_a_reconnect_base_seconds: int = 1
    news_provider_a_reconnect_max_seconds: int = 60
    news_provider_a_max_retries: int = -1  # -1 => infinite

    # Provider B
    news_provider_b_enabled: bool = False
    news_provider_b_name: str = ""
    news_provider_b_protocol: ProviderProtocol = ProviderProtocol.http
    news_provider_b_url: str = ""
    news_provider_b_api_key: str = ""
    news_provider_b_timeout_seconds: int = 20
    news_provider_b_heartbeat_interval_seconds: int = 30
    news_provider_b_reconnect_base_seconds: int = 1
    news_provider_b_reconnect_max_seconds: int = 60
    news_provider_b_max_retries: int = 10

    # Provider C
    news_provider_c_enabled: bool = True
    news_provider_c_name: str = "MarketAux"
    news_provider_c_protocol: ProviderProtocol = ProviderProtocol.http
    news_provider_c_url: str = ""
    news_provider_c_api_key: str = ""
    news_provider_c_timeout_seconds: int = 20

    # Provider D
    news_provider_d_enabled: bool = True
    news_provider_d_name: str = "FRED"
    news_provider_d_protocol: ProviderProtocol = ProviderProtocol.http
    news_provider_d_url: str = ""
    news_provider_d_api_key: str = ""
    news_provider_d_timeout_seconds: int = 20

    # Global
    news_ingestion_loop_interval_seconds: int = Field(default=15, gt=0)
    news_log_level: LogLevel = LogLevel.INFO

    # N/M/K settings
    ws_heartbeat_ping_interval_seconds: int = Field(default=15, ge=1)
    ws_heartbeat_pong_timeout_seconds: int = Field(default=5, ge=1)
    ws_heartbeat_missed_pongs_threshold: int = Field(default=3, ge=1)
    
    @model_validator(mode="after")
    def validate_ingestion_contract(self):
        self._validate_provider(
            key="A",
            enabled=self.news_provider_a_enabled,
            protocol=self.news_provider_a_protocol,
            url=self.news_provider_a_url,
            api_key=self.news_provider_a_api_key,
            heartbeat=self.news_provider_a_heartbeat_interval_seconds,
            reconnect_base=self.news_provider_a_reconnect_base_seconds,
            reconnect_max=self.news_provider_a_reconnect_max_seconds,
            max_retries=self.news_provider_a_max_retries,
        )
        self._validate_provider(
            key="B",
            enabled=self.news_provider_b_enabled,
            protocol=self.news_provider_b_protocol,
            url=self.news_provider_b_url,
            api_key=self.news_provider_b_api_key,
            heartbeat=self.news_provider_b_heartbeat_interval_seconds,
            reconnect_base=self.news_provider_b_reconnect_base_seconds,
            reconnect_max=self.news_provider_b_reconnect_max_seconds,
            max_retries=self.news_provider_b_max_retries,
        )

        # C/D optional enrichment/context: validate required fields when enabled
        if self.news_provider_c_enabled:
            if not self.news_provider_c_url.strip():
                raise ValueError("NEWS_PROVIDER_C_URL is required when provider C is enabled.")
            if not self.news_provider_c_api_key.strip():
                raise ValueError("NEWS_PROVIDER_C_API_KEY is required when provider C is enabled.")

        if self.news_provider_d_enabled:
            if not self.news_provider_d_url.strip():
                raise ValueError("NEWS_PROVIDER_D_URL is required when provider D is enabled.")
            # If your chosen FRED endpoints do not require key, relax this later.
            if not self.news_provider_d_api_key.strip():
                raise ValueError("NEWS_PROVIDER_D_API_KEY is required when provider D is enabled.")

        return self

    @staticmethod
    def _validate_provider(
        *,
        key: str,
        enabled: bool,
        protocol: ProviderProtocol,
        url: str,
        api_key: str,
        heartbeat: int,
        reconnect_base: int,
        reconnect_max: int,
        max_retries: int,
    ) -> None:
        if not enabled:
            return

        if protocol not in (ProviderProtocol.ws, ProviderProtocol.http):
            raise ValueError(f"NEWS_PROVIDER_{key}_PROTOCOL must be 'ws' or 'http'.")

        if not url.strip():
            raise ValueError(f"NEWS_PROVIDER_{key}_URL is required when provider {key} is enabled.")

        if not api_key.strip():
            raise ValueError(
        f"NEWS_PROVIDER_{key}_API_KEY is required when provider {key} is enabled."
    )

        if protocol == ProviderProtocol.ws and heartbeat <= 0:
            raise ValueError(
                f"NEWS_PROVIDER_{key}_HEARTBEAT_INTERVAL_SECONDS must be > 0 for ws providers."
            )

        if reconnect_base <= 0:
            raise ValueError(f"NEWS_PROVIDER_{key}_RECONNECT_BASE_SECONDS must be > 0.")

        if reconnect_max < reconnect_base:
            raise ValueError(
                f"NEWS_PROVIDER_{key}_RECONNECT_MAX_SECONDS must be >= RECONNECT_BASE_SECONDS."
            )

        if not (max_retries == -1 or max_retries >= 0):
            raise ValueError(
                f"NEWS_PROVIDER_{key}_MAX_RETRIES must be -1 (infinite) or >= 0."
            )