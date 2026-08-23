import secrets
import uuid
from datetime import timedelta

from sqlalchemy import update, select
from sqlalchemy.orm import Session

from app.core.security import hash_token, utcnow
from app.models.authentication import PreAuthSession
from app.models.email_settings import EmailMfaChallenge
from app.models.user import User
from app.services.authentication_settings_service import get_or_create_authentication_settings
from app.services.audit_service import write_audit
from app.services.email import send_configured_email
from app.services.email.templates import email_mfa_code


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "configured account"
    masked_local = local[:1] + "***" if len(local) <= 2 else f"{local[:2]}***{local[-1:]}"
    return f"{masked_local}@{domain}"


def send_email_mfa_code(db: Session, *, user: User, pre_auth_session: PreAuthSession, ip_address: str | None) -> EmailMfaChallenge:
    auth_settings = get_or_create_authentication_settings(db)
    code = f"{secrets.randbelow(1_000_000):06d}"
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
        code_hash=hash_token(code),
        expires_at=now + timedelta(minutes=auth_settings.mfa_code_expiration_minutes),
        ip_address=ip_address,
    )
    pre_auth_session.last_sent_at = now
    db.add(challenge)
    db.flush()
    send_configured_email(db, email_mfa_code(to=user.email, code=code, expires_minutes=auth_settings.mfa_code_expiration_minutes))
    write_audit(db, event_type="EMAIL_MFA_CODE_SENT", result="SUCCESS", user_id=user.id, ip_address=ip_address)
    return challenge


def verify_email_mfa_code(db: Session, *, pre_auth_session: PreAuthSession, code: str, ip_address: str | None) -> User | None:
    auth_settings = get_or_create_authentication_settings(db)
    user = db.get(User, pre_auth_session.user_id)
    if not user or not user.enabled:
        return None
    challenge = db.scalar(
        select(EmailMfaChallenge)
        .where(
            EmailMfaChallenge.pre_auth_session_id == pre_auth_session.id,
            EmailMfaChallenge.used_at.is_(None),
            EmailMfaChallenge.invalidated_at.is_(None),
        )
        .order_by(EmailMfaChallenge.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    now = utcnow()
    if not challenge or pre_auth_session.completed_at or pre_auth_session.cancelled_at or pre_auth_session.expires_at <= now:
        write_audit(db, event_type="EMAIL_MFA_VERIFY", result="FAILURE", user_id=user.id, ip_address=ip_address)
        db.flush()
        return None
    if challenge.expires_at <= now or challenge.attempts >= auth_settings.mfa_max_attempts:
        challenge.invalidated_at = now
        pre_auth_session.cancelled_at = now
        write_audit(db, event_type="EMAIL_MFA_VERIFY", result="FAILURE", user_id=user.id, ip_address=ip_address, metadata={"reason": "expired_or_attempts"})
        db.flush()
        return None
    challenge.attempts += 1
    if challenge.code_hash != hash_token(code):
        if challenge.attempts >= auth_settings.mfa_max_attempts:
            challenge.invalidated_at = now
            pre_auth_session.cancelled_at = now
        write_audit(db, event_type="EMAIL_MFA_VERIFY", result="FAILURE", user_id=user.id, ip_address=ip_address)
        db.flush()
        return None
    challenge.used_at = now
    pre_auth_session.completed_at = now
    write_audit(db, event_type="EMAIL_MFA_VERIFY", result="SUCCESS", user_id=user.id, ip_address=ip_address)
    db.flush()
    return user


def get_pre_auth_session(db: Session, token: str | None) -> PreAuthSession | None:
    if not token:
        return None
    return db.scalar(select(PreAuthSession).where(PreAuthSession.token_hash == hash_token(token)).with_for_update())


def cancel_pre_auth_session(db: Session, *, pre_auth_session: PreAuthSession, ip_address: str | None) -> None:
    now = utcnow()
    pre_auth_session.cancelled_at = now
    db.execute(
        update(EmailMfaChallenge)
        .where(EmailMfaChallenge.pre_auth_session_id == pre_auth_session.id, EmailMfaChallenge.used_at.is_(None))
        .values(invalidated_at=now)
    )
    write_audit(db, event_type="EMAIL_MFA_CANCELLED", result="SUCCESS", user_id=pre_auth_session.user_id, ip_address=ip_address)
    db.flush()


def invalidate_user_mfa_state(db: Session, user_id: uuid.UUID) -> None:
    now = utcnow()
    db.execute(
        update(PreAuthSession)
        .where(PreAuthSession.user_id == user_id, PreAuthSession.completed_at.is_(None), PreAuthSession.cancelled_at.is_(None))
        .values(cancelled_at=now)
    )
    db.execute(
        update(EmailMfaChallenge)
        .where(EmailMfaChallenge.user_id == user_id, EmailMfaChallenge.used_at.is_(None), EmailMfaChallenge.invalidated_at.is_(None))
        .values(invalidated_at=now)
    )
