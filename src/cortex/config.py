import os
from functools import lru_cache
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
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
    cortex_ui_enabled: bool = Field(default=False, alias="CORTEX_UI_ENABLED")
    cortex_internal_admin_session_enabled: bool = Field(
        default=False, alias="CORTEX_INTERNAL_ADMIN_SESSION_ENABLED"
    )
    cortex_auth_provider: Literal["local", "oidc", "clerk", "auth0", "supabase"] = (
        Field(default="local", alias="CORTEX_AUTH_PROVIDER")
    )
    cortex_public_auth_enabled: bool = Field(
        default=False, alias="CORTEX_PUBLIC_AUTH_ENABLED"
    )
    cortex_required_terms_version: str = Field(
        default="terms-v1", alias="CORTEX_REQUIRED_TERMS_VERSION"
    )
    cortex_ui_session_secret: str = Field(default="", alias="CORTEX_UI_SESSION_SECRET")
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
    cortex_provider_acl_refresh_targets_json: str = Field(
        default="", alias="CORTEX_PROVIDER_ACL_REFRESH_TARGETS_JSON"
    )
    cortex_provider_acl_principal_mappings_json: str = Field(
        default="", alias="CORTEX_PROVIDER_ACL_PRINCIPAL_MAPPINGS_JSON"
    )
    cortex_provider_acl_refresh_lease_ttl_seconds: int = Field(
        default=600, alias="CORTEX_PROVIDER_ACL_REFRESH_LEASE_TTL_SECONDS"
    )
    cortex_provider_acl_snapshot_ttl_hours: int = Field(
        default=24, alias="CORTEX_PROVIDER_ACL_SNAPSHOT_TTL_HOURS"
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
    stripe_api_key: str = Field(default="", alias="STRIPE_API_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id: str = Field(default="", alias="STRIPE_PRICE_ID")
    stripe_success_url: str = Field(default="", alias="STRIPE_SUCCESS_URL")
    stripe_cancel_url: str = Field(default="", alias="STRIPE_CANCEL_URL")
    stripe_portal_return_url: str = Field(default="", alias="STRIPE_PORTAL_RETURN_URL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    cortex_secret_encryption_key: str = Field(
        default="", alias="CORTEX_SECRET_ENCRYPTION_KEY"
    )
    cortex_secret_encryption_key_version: str = Field(
        default="local-v1", alias="CORTEX_SECRET_ENCRYPTION_KEY_VERSION"
    )
    database_url: str = Field(default="", alias="DATABASE_URL")
    kafka_bootstrap_servers: str = Field(default="", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_consumer_group: str = Field(
        default="cortex-pipeline-v1", alias="KAFKA_CONSUMER_GROUP"
    )
    payload_store_path: str = Field(default="", alias="PAYLOAD_STORE_PATH")
    object_storage_endpoint: str = Field(default="", alias="OBJECT_STORAGE_ENDPOINT")
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    qdrant_collection_prefix: str = Field(
        default="cortex", alias="QDRANT_COLLECTION_PREFIX"
    )
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

    @field_validator("qdrant_url")
    @classmethod
    def validate_qdrant_url(cls, value: str) -> str:
        value = value.rstrip("/")
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("QDRANT_URL must be an absolute http(s) URL")
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError(
                "QDRANT_URL must not contain credentials, query, or fragment"
            )
        return value

    @field_validator("qdrant_collection_prefix")
    @classmethod
    def validate_qdrant_collection_prefix(cls, value: str) -> str:
        from cortex.indexing.qdrant import validate_collection_name

        validate_collection_name(value)
        return value

    @model_validator(mode="after")
    def validate_hosted_qdrant_credentials(self) -> "Settings":
        if (
            self.qdrant_url
            and (
                not _is_local_qdrant_url(self.qdrant_url) or self.qdrant_api_key.strip()
            )
            and urlparse(self.qdrant_url).scheme != "https"
        ):
            raise ValueError("hosted QDRANT_URL and QDRANT_API_KEY require HTTPS")
        if (
            self.qdrant_url
            and not _is_local_qdrant_url(self.qdrant_url)
            and not self.qdrant_api_key.strip()
        ):
            raise ValueError("QDRANT_API_KEY is required for hosted QDRANT_URL")
        return self

    def qdrant_collection_name(
        self,
        *,
        embedding_model: str,
        embedding_version: str,
        dimensions: int,
    ) -> str:
        """Build the environment/model/version collection name used by Qdrant.

        Callers must provide stable model and version identifiers; this method
        intentionally validates rather than silently rewriting those identities.
        """
        name = (
            f"{self.qdrant_collection_prefix}-{self.cortex_env}-"
            f"{embedding_model}-{embedding_version}-{dimensions}"
        )
        from cortex.indexing.qdrant import validate_collection_name

        validate_collection_name(name)
        return name


def _is_local_qdrant_url(value: str) -> bool:
    host = urlparse(value).hostname
    return host in {"localhost", "127.0.0.1", "::1", "qdrant", "host.docker.internal"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
