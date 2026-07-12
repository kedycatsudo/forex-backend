import os
import pytest

from app.ingestion.config import IngestionSettings


@pytest.fixture(autouse=True)
def clear_news_env():
    keys = [k for k in os.environ if k.startswith("NEWS_")]
    for k in keys:
        os.environ.pop(k, None)
    yield
    keys = [k for k in os.environ if k.startswith("NEWS_")]
    for k in keys:
        os.environ.pop(k, None)


def set_valid_base_env():
    os.environ["NEWS_PROVIDER_A_ENABLED"] = "true"
    os.environ["NEWS_PROVIDER_A_NAME"] = "TradingEconomics"
    os.environ["NEWS_PROVIDER_A_PROTOCOL"] = "http"
    os.environ["NEWS_PROVIDER_A_URL"] = "https://api.tradingeconomics.com"
    os.environ["NEWS_PROVIDER_A_API_KEY"] = "x"
    os.environ["NEWS_PROVIDER_A_TIMEOUT_SECONDS"] = "15"
    os.environ["NEWS_PROVIDER_A_HEARTBEAT_INTERVAL_SECONDS"] = "30"
    os.environ["NEWS_PROVIDER_A_RECONNECT_BASE_SECONDS"] = "1"
    os.environ["NEWS_PROVIDER_A_RECONNECT_MAX_SECONDS"] = "60"
    os.environ["NEWS_PROVIDER_A_MAX_RETRIES"] = "-1"

    os.environ["NEWS_PROVIDER_B_ENABLED"] = "false"

    os.environ["NEWS_PROVIDER_C_ENABLED"] = "false"
    os.environ["NEWS_PROVIDER_D_ENABLED"] = "false"

    os.environ["NEWS_INGESTION_LOOP_INTERVAL_SECONDS"] = "15"
    os.environ["NEWS_LOG_LEVEL"] = "INFO"


def test_valid_config_passes():
    set_valid_base_env()
    s = IngestionSettings()
    assert s.news_provider_a_enabled is True


def test_invalid_protocol_fails():
    set_valid_base_env()
    os.environ["NEWS_PROVIDER_A_PROTOCOL"] = "websocket"
    with pytest.raises(Exception):
        IngestionSettings()


def test_enabled_provider_missing_url_fails():
    set_valid_base_env()
    os.environ["NEWS_PROVIDER_A_URL"] = ""
    with pytest.raises(Exception):
        IngestionSettings()


def test_enabled_provider_missing_api_key_fails():
    set_valid_base_env()
    os.environ["NEWS_PROVIDER_A_API_KEY"] = ""
    with pytest.raises(Exception):
        IngestionSettings()


def test_ws_heartbeat_must_be_positive():
    set_valid_base_env()
    os.environ["NEWS_PROVIDER_A_PROTOCOL"] = "ws"
    os.environ["NEWS_PROVIDER_A_HEARTBEAT_INTERVAL_SECONDS"] = "0"
    with pytest.raises(Exception):
        IngestionSettings()


def test_reconnect_max_must_be_gte_base():
    set_valid_base_env()
    os.environ["NEWS_PROVIDER_A_RECONNECT_BASE_SECONDS"] = "10"
    os.environ["NEWS_PROVIDER_A_RECONNECT_MAX_SECONDS"] = "5"
    with pytest.raises(Exception):
        IngestionSettings()


def test_max_retries_must_be_minus1_or_nonnegative():
    set_valid_base_env()
    os.environ["NEWS_PROVIDER_A_MAX_RETRIES"] = "-2"
    with pytest.raises(Exception):
        IngestionSettings()


def test_loop_interval_must_be_positive():
    set_valid_base_env()
    os.environ["NEWS_INGESTION_LOOP_INTERVAL_SECONDS"] = "0"
    with pytest.raises(Exception):
        IngestionSettings()