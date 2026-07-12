from app.ingestion.config import IngestionSettings


def build_ingestion_settings() -> IngestionSettings:
    settings = IngestionSettings()  # triggers validation
    return settings


def ingestion_settings_summary(settings: IngestionSettings) -> dict:
    return {
        "provider_a": {
            "enabled": settings.news_provider_a_enabled,
            "name": settings.news_provider_a_name,
            "protocol": settings.news_provider_a_protocol.value,
            "url": settings.news_provider_a_url,
            "api_key_set": bool(settings.news_provider_a_api_key),
        },
        "provider_b": {
            "enabled": settings.news_provider_b_enabled,
            "name": settings.news_provider_b_name,
            "protocol": settings.news_provider_b_protocol.value,
            "url": settings.news_provider_b_url,
            "api_key_set": bool(settings.news_provider_b_api_key),
        },
        "global": {
            "loop_interval_seconds": settings.news_ingestion_loop_interval_seconds,
            "log_level": settings.news_log_level.value,
        },
    }