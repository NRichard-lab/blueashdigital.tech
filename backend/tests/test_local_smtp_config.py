import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_smtp_host() -> None:
    with pytest.raises(ValidationError, match="SMTP_HOST is local-development only"):
        Settings(
            _env_file=None,
            app_env="production",
            smtp_host="mailpit",
            opportunity_radar_client_secret="x" * 32,
            opportunity_radar_client_id="opportunity-radar",
            opportunity_radar_public_origin="https://radar.blueashdigital.tech",
            opportunity_radar_callback_uri="https://radar.blueashdigital.tech/api/auth/callback",
            session_cookie_name="__Host-blueash_portal_session",
            pre_auth_cookie_name="__Host-blueash_pre_auth",
        )
