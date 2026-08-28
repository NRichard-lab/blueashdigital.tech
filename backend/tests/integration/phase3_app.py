from __future__ import annotations

import os
from datetime import timedelta

from sqlalchemy import update
from sqlalchemy.engine import make_url


def _require_synthetic_mode() -> str:
    if os.environ.get("PHASE3_SYNTHETIC_TEST_MODE") != "1":
        raise RuntimeError("The Phase 3 test application is disabled.")
    if os.environ.get("PHASE3_ALLOW_DISPOSABLE_DATABASE") != "1":
        raise RuntimeError("The Phase 3 test application requires an explicitly disposable database.")
    if os.environ.get("APP_ENV") != "production":
        raise RuntimeError("Phase 3 browser tests must exercise production cookie flags.")
    url = make_url(os.environ.get("DATABASE_URL", ""))
    if url.database != "portal_phase3" or url.host != "portal-postgres":
        raise RuntimeError("The Phase 3 test application may only use isolated portal_phase3 PostgreSQL.")
    code = os.environ.get("PHASE3_SYNTHETIC_MFA_CODE", "")
    if len(code) != 6 or not code.isdigit():
        raise RuntimeError("PHASE3_SYNTHETIC_MFA_CODE must be six digits.")
    return code


SYNTHETIC_MFA_CODE = _require_synthetic_mode()

from app.api import auth as auth_api  # noqa: E402
from app.core.security import hash_token, utcnow  # noqa: E402
from app.models.email_settings import EmailMfaChallenge  # noqa: E402
from app.services.audit_service import write_audit  # noqa: E402
from app.services.authentication_settings_service import get_or_create_authentication_settings  # noqa: E402


def _send_synthetic_mfa_code(db, *, user, pre_auth_session, ip_address):
    auth_settings = get_or_create_authentication_settings(db)
    now = utcnow()
    db.execute(
        update(EmailMfaChallenge)
        .where(
            EmailMfaChallenge.user_id == user.id,
            EmailMfaChallenge.used_at.is_(None),
            EmailMfaChallenge.invalidated_at.is_(None),
        )
        .values(invalidated_at=now)
    )
    challenge = EmailMfaChallenge(
        user_id=user.id,
        pre_auth_session_id=pre_auth_session.id,
        code_hash=hash_token(SYNTHETIC_MFA_CODE),
        expires_at=now + timedelta(minutes=auth_settings.mfa_code_expiration_minutes),
        ip_address=ip_address,
    )
    pre_auth_session.last_sent_at = now
    db.add(challenge)
    db.flush()
    write_audit(
        db,
        event_type="EMAIL_MFA_CODE_SENT",
        result="SUCCESS",
        user_id=user.id,
        ip_address=ip_address,
        metadata={"transport": "synthetic_phase3_sink"},
    )
    return challenge


auth_api.send_email_mfa_code = _send_synthetic_mfa_code

from app.main import app  # noqa: E402,F401
