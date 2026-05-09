import os
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

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
    cortex_linear_connector_enabled: bool = Field(
        default=False, alias="CORTEX_LINEAR_CONNECTOR_ENABLED"
    )
    cortex_github_connector_enabled: bool = Field(
        default=False, alias="CORTEX_GITHUB_CONNECTOR_ENABLED"
    )
    cortex_repo_docs_connector_enabled: bool = Field(
        default=False, alias="CORTEX_REPO_DOCS_CONNECTOR_ENABLED"
    )
    cortex_context_gate_blocking_enabled: bool = Field(
        default=False, alias="CORTEX_CONTEXT_GATE_BLOCKING_ENABLED"
    )
    cortex_embedding_mode: Literal["deterministic", "real"] = Field(
        default="deterministic", alias="CORTEX_EMBEDDING_MODE"
    )
    cortex_event_bus: Literal["memory", "kafka"] = Field(
        default="memory", alias="CORTEX_EVENT_BUS"
    )
    cortex_state_backend: Literal["memory", "sql"] = Field(
        default="memory", alias="CORTEX_STATE_BACKEND"
    )
    cortex_cache_backend: Literal["memory", "redis"] = Field(
        default="memory", alias="CORTEX_CACHE_BACKEND"
    )
    cortex_api_rate_limit_enabled: bool = Field(
        default=False, alias="CORTEX_API_RATE_LIMIT_ENABLED"
    )
    cortex_api_rate_limit_requests: int = Field(
        default=120, alias="CORTEX_API_RATE_LIMIT_REQUESTS"
    )
    cortex_api_rate_limit_window_seconds: int = Field(
        default=60, alias="CORTEX_API_RATE_LIMIT_WINDOW_SECONDS"
    )
    cortex_provider_rate_limit_enabled: bool = Field(
        default=False, alias="CORTEX_PROVIDER_RATE_LIMIT_ENABLED"
    )
    cortex_provider_rate_limit_requests: int = Field(
        default=60, alias="CORTEX_PROVIDER_RATE_LIMIT_REQUESTS"
    )
    cortex_provider_rate_limit_window_seconds: int = Field(
        default=60, alias="CORTEX_PROVIDER_RATE_LIMIT_WINDOW_SECONDS"
    )
    cortex_model_rate_limit_enabled: bool = Field(
        default=False, alias="CORTEX_MODEL_RATE_LIMIT_ENABLED"
    )
    cortex_model_rate_limit_requests: int = Field(
        default=120, alias="CORTEX_MODEL_RATE_LIMIT_REQUESTS"
    )
    cortex_model_rate_limit_window_seconds: int = Field(
        default=60, alias="CORTEX_MODEL_RATE_LIMIT_WINDOW_SECONDS"
    )
    slack_client_id: str = Field(default="", alias="SLACK_CLIENT_ID")
    slack_client_secret: str = Field(default="", alias="SLACK_CLIENT_SECRET")
    slack_signing_secret: str = Field(default="", alias="SLACK_SIGNING_SECRET")
    slack_redirect_uri: str = Field(default="", alias="SLACK_REDIRECT_URI")
    slack_team_id: str = Field(default="", alias="SLACK_TEAM_ID")
    linear_api_token: str = Field(default="", alias="LINEAR_API_TOKEN")
    github_app_id: str = Field(default="", alias="GITHUB_APP_ID")
    github_private_key: str = Field(default="", alias="GITHUB_PRIVATE_KEY")
    github_installation_token: str = Field(
        default="", alias="GITHUB_INSTALLATION_TOKEN"
    )
    github_webhook_secret: str = Field(default="", alias="GITHUB_WEBHOOK_SECRET")
    database_url: str = Field(default="", alias="DATABASE_URL")
    kafka_bootstrap_servers: str = Field(default="", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_consumer_group: str = Field(
        default="cortex-pipeline-v1", alias="KAFKA_CONSUMER_GROUP"
    )
    payload_store_path: str = Field(default="", alias="PAYLOAD_STORE_PATH")
    object_storage_endpoint: str = Field(default="", alias="OBJECT_STORAGE_ENDPOINT")
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    redis_url: str = Field(default="", alias="REDIS_URL")
    otel_exporter_otlp_endpoint: str = Field(
        default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    cortex_otel_enabled: bool = Field(default=False, alias="CORTEX_OTEL_ENABLED")
    cortex_service_name: str = Field(default="cortex", alias="CORTEX_SERVICE_NAME")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_file = os.getenv("CORTEX_CONFIG_FILE")
        include_dotenv = not os.getenv("CORTEX_DISABLE_DOTENV")
        if not yaml_file:
            if not include_dotenv:
                return (
                    init_settings,
                    env_settings,
                    file_secret_settings,
                )
            return (
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
            )
        yaml_settings = YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file)
        if not include_dotenv:
            return (
                init_settings,
                env_settings,
                yaml_settings,
                file_secret_settings,
            )
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_settings,
            file_secret_settings,
        )

    def sanitized_dict(self) -> dict[str, Any]:
        return redact_mapping(self.model_dump(mode="json"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
