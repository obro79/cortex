from functools import lru_cache
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cortex.observability.logging import redact_mapping


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", populate_by_name=True
    )

    cortex_env: Literal["local", "test", "staging", "production"] = Field(
        default="local", alias="CORTEX_ENV"
    )
    cortex_log_level: str = Field(default="INFO", alias="CORTEX_LOG_LEVEL")
    cortex_dev_workbench_enabled: bool = Field(
        default=False, alias="CORTEX_DEV_WORKBENCH_ENABLED"
    )
    cortex_slack_connector_enabled: bool = Field(
        default=False, alias="CORTEX_SLACK_CONNECTOR_ENABLED"
    )
    slack_signing_secret: str = Field(default="", alias="SLACK_SIGNING_SECRET")
    database_url: str = Field(default="", alias="DATABASE_URL")
    kafka_bootstrap_servers: str = Field(default="", alias="KAFKA_BOOTSTRAP_SERVERS")
    object_storage_endpoint: str = Field(default="", alias="OBJECT_STORAGE_ENDPOINT")
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    redis_url: str = Field(default="", alias="REDIS_URL")
    otel_exporter_otlp_endpoint: str = Field(
        default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )

    def sanitized_dict(self) -> dict[str, Any]:
        return redact_mapping(self.model_dump(mode="json"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
