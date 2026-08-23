from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.authentication import AuthenticationSettings


AUTH_LIMITS = {
    "idle_timeout_minutes": (5, 480),
    "absolute_timeout_minutes": (30, 1440),
    "mfa_code_expiration_minutes": (2, 15),
    "mfa_max_attempts": (3, 10),
    "mfa_resend_delay_seconds": (30, 300),
}

AUTH_DEFAULTS = {
    "idle_timeout_minutes": 30,
    "absolute_timeout_minutes": 480,
    "mfa_code_expiration_minutes": 10,
    "mfa_max_attempts": 5,
    "mfa_resend_delay_seconds": 60,
}


def clamp_auth_value(name: str, value: int) -> int:
    low, high = AUTH_LIMITS[name]
    return max(low, min(high, int(value)))


def get_or_create_authentication_settings(db: Session) -> AuthenticationSettings:
    auth_settings = db.scalar(select(AuthenticationSettings).order_by(AuthenticationSettings.created_at.asc()).limit(1))
    if auth_settings:
        changed = False
        for name, default in AUTH_DEFAULTS.items():
            value = getattr(auth_settings, name) or default
            clamped = clamp_auth_value(name, value)
            if value != clamped:
                setattr(auth_settings, name, clamped)
                changed = True
        if changed:
            db.flush()
        return auth_settings
    auth_settings = AuthenticationSettings(**AUTH_DEFAULTS)
    db.add(auth_settings)
    db.flush()
    return auth_settings
