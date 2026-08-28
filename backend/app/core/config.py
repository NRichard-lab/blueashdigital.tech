from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Blue Ash Digital Portal"
    app_domain: str = "blueashdigital.tech"
    frontend_origin: str = "http://localhost:5173"
    cors_origins: str | None = None
    database_url: str = "postgresql+psycopg://portal:portal-dev-password@postgres:5432/portal"
    secret_key: str = Field(default="dev-only-secret")
    session_secret: str = Field(default="dev-only-session-secret")
    email_encryption_key: str | None = None
    session_cookie_name: str = "blueash_session"
    pre_auth_cookie_name: str = "blueash_pre_auth"
    session_max_age_seconds: int = 60 * 60 * 8
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from: str = "no-reply@blueashdigital.tech"
    opportunity_radar_client_id: str = "opportunity-radar"
    opportunity_radar_client_secret: str | None = None
    opportunity_radar_public_origin: str = "https://radar.blueashdigital.tech"
    opportunity_radar_callback_uri: str = "https://radar.blueashdigital.tech/api/auth/callback"
    application_auth_code_ttl_seconds: int = Field(default=60, ge=30, le=120)
    application_session_idle_seconds: int = Field(default=30 * 60, ge=300, le=3600)
    application_session_absolute_max_seconds: int = Field(default=8 * 60 * 60, ge=1800, le=86400)
    application_auth_cleanup_retention_seconds: int = Field(default=24 * 60 * 60, ge=3600, le=2592000)

    @model_validator(mode="after")
    def validate_production_application_auth(self) -> "Settings":
        if not self.is_production:
            return self
        secret = self.opportunity_radar_client_secret or ""
        if len(secret) < 32 or secret.lower().startswith(("change-me", "replace-me", "dev-only")):
            raise ValueError("OPPORTUNITY_RADAR_CLIENT_SECRET must be a strong production secret of at least 32 characters")
        if self.opportunity_radar_client_id != "opportunity-radar":
            raise ValueError("OPPORTUNITY_RADAR_CLIENT_ID must identify the registered Opportunity Radar client")
        if self.opportunity_radar_public_origin != "https://radar.blueashdigital.tech":
            raise ValueError("OPPORTUNITY_RADAR_PUBLIC_ORIGIN must be the exact production Radar origin")
        if self.opportunity_radar_callback_uri != "https://radar.blueashdigital.tech/api/auth/callback":
            raise ValueError("OPPORTUNITY_RADAR_CALLBACK_URI must be the exact registered production callback")
        if not self.session_cookie_name.startswith("__Host-") or not self.pre_auth_cookie_name.startswith("__Host-"):
            raise ValueError("Production authentication cookie names must use the __Host- prefix")
        if self.session_cookie_name == self.pre_auth_cookie_name:
            raise ValueError("Portal session and pre-authentication cookies must use distinct names")
        if self.application_auth_code_ttl_seconds != 60:
            raise ValueError("Production application authorization codes must expire after exactly 60 seconds")
        if self.application_session_idle_seconds != 1800:
            raise ValueError("Production application sessions must use a 30-minute idle timeout")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def allowed_cors_origins(self) -> list[str]:
        configured = self.cors_origins or self.frontend_origin
        return list(
            dict.fromkeys(
                origin.strip().rstrip("/")
                for origin in configured.split(",")
                if origin.strip()
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

