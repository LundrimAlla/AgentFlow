from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "test", "production"] = "development"
    cors_origins: list[str] = ["http://localhost:3000"]
    live_enabled: bool = False
    chat_timeout_seconds: float = Field(default=60, gt=0, le=60)
    provider_timeout_seconds: float = Field(default=25, gt=0, le=25)
    rag_enabled: bool = False
    rag_database_url: SecretStr = SecretStr("")
    telemetry_enabled: bool = False
    telemetry_database_url: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("")  # Operator CLI only; never supplied to API container.
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: Literal["gemini-3.5-flash-lite"] = "gemini-3.5-flash-lite"
    turnstile_secret_key: SecretStr = SecretStr("")
    turnstile_hostnames: list[str] = ["localhost", "127.0.0.1"]
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: SecretStr = SecretStr("")
    rate_limit_hmac_secret: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def require_live_configuration(self) -> "Settings":
        if self.telemetry_enabled and not self.telemetry_database_url.get_secret_value():
            raise ValueError("Telemetry requires a restricted metrics database URL")
        if self.rag_enabled and (
            not self.live_enabled or not self.rag_database_url.get_secret_value()
        ):
            raise ValueError("Retrieval requires live mode and a read-only database URL")
        if not self.live_enabled:
            return self
        from urllib.parse import urlsplit

        url = urlsplit(self.upstash_redis_rest_url)
        if (
            url.scheme != "https"
            or not (url.hostname or "").endswith(".upstash.io")
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in ("", "/")
            or url.port not in (None, 443)
        ):
            raise ValueError("A valid HTTPS Upstash endpoint is required")
        secrets = (
            self.gemini_api_key,
            self.turnstile_secret_key,
            self.upstash_redis_rest_token,
            self.rate_limit_hmac_secret,
        )
        if any(not value.get_secret_value().strip() for value in secrets):
            raise ValueError("Live credentials are incomplete")
        if len(self.rate_limit_hmac_secret.get_secret_value()) < 32:
            raise ValueError("A random HMAC secret of at least 32 characters is required")
        if self.turnstile_secret_key.get_secret_value().startswith(("1x", "2x", "3x")):
            raise ValueError("Turnstile test keys cannot protect live AI")
        if not self.turnstile_hostnames or any("*" in h for h in self.turnstile_hostnames):
            raise ValueError("Explicit Turnstile hostnames are required")
        return self

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcards(cls, origins: list[str]) -> list[str]:
        if any("*" in origin for origin in origins):
            raise ValueError("Explicit CORS origins are required")
        return origins
