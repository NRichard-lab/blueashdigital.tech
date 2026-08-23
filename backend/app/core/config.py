from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Blue Ash Digital Portal"
    app_domain: str = "blueashdigital.tech"
    frontend_origin: str = "http://localhost:5173"
    cookie_domain: str | None = None
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

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

