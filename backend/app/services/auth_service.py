from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.security import generate_token, hash_token, utcnow, verify_password
from app.models.authentication import PreAuthSession
from app.models.email_settings import EmailMfaChallenge
from app.models.password_reset import PasswordResetToken
from app.models.session import PortalSession
from app.models.user import Role, User
from app.services.authentication_settings_service import get_or_create_authentication_settings
from app.services.audit_service import write_audit


@dataclass(frozen=True)
class PortalSessionContext:
    session: PortalSession
    user: User


def mfa_required_for_user(user: User) -> bool:
    return user.role == Role.ADMINISTRATOR or user.mfa_required


def authenticate_password(db: Session, *, identifier: str, password: str, ip_address: str | None) -> User | None:
    normalized = identifier.strip().lower()
    user = db.scalar(select(User).where(or_(User.username == normalized, User.email == normalized)))

    if not user or not user.enabled or not verify_password(password, user.password_hash):
        write_audit(db, event_type="LOGIN_FAILED", result="FAILURE", ip_address=ip_address, metadata={"identifier": normalized[:120]})
        db.commit()
        return None
    return user


def create_pre_auth_session(
    db: Session,
    *,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
    return_to: str | None = None,
) -> tuple[PreAuthSession, str]:
    auth_settings = get_or_create_authentication_settings(db)
    token = generate_token()
    pre_auth = PreAuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        ip_address=ip_address,
        user_agent=user_agent[:512] if user_agent else None,
        expires_at=utcnow() + timedelta(minutes=auth_settings.mfa_code_expiration_minutes),
        return_to=return_to,
    )
    db.add(pre_auth)
    db.flush()
    return pre_auth, token


def create_session_for_user(
    db: Session,
    *,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
    mfa_satisfied: bool = False,
) -> tuple[User, str, int]:
    auth_settings = get_or_create_authentication_settings(db)
    token = generate_token()
    now = utcnow()
    idle_seconds = auth_settings.idle_timeout_minutes * 60
    session = PortalSession(
        user_id=user.id,
        session_hash=hash_token(token),
        ip_address=ip_address,
        user_agent=user_agent[:512] if user_agent else None,
        last_activity_at=now,
        mfa_satisfied_at=now if mfa_satisfied else None,
        expires_at=now + timedelta(seconds=idle_seconds),
        absolute_expires_at=now + timedelta(minutes=auth_settings.absolute_timeout_minutes),
    )
    user.last_login_at = now
    db.add(session)
    write_audit(db, event_type="LOGIN_SUCCESSFUL", result="SUCCESS", user_id=user.id, ip_address=ip_address)
    return user, token, idle_seconds


def get_portal_session_context(db: Session, token: str | None) -> PortalSessionContext | None:
    if not token:
        return None

    session = db.scalar(select(PortalSession).where(PortalSession.session_hash == hash_token(token)))
    if not session or session.revoked_at:
        return None
    auth_settings = get_or_create_authentication_settings(db)
    now = utcnow()
    idle_expired = session.last_activity_at + timedelta(minutes=auth_settings.idle_timeout_minutes) <= now
    absolute_expired = session.absolute_expires_at <= now
    if idle_expired or absolute_expired or session.expires_at <= now:
        session.revoked_at = now
        from app.services.application_auth_service import revoke_application_auth_for_parent

        revoke_application_auth_for_parent(db, session.id, reason="PARENT_SESSION_EXPIRED")
        write_audit(
            db,
            event_type="SESSION_EXPIRED",
            result="SUCCESS",
            user_id=session.user_id,
            ip_address=session.ip_address,
            metadata={"reason": "absolute" if absolute_expired else "idle"},
        )
        db.commit()
        return None

    user = db.get(User, session.user_id)
    if not user or not user.enabled:
        session.revoked_at = now
        from app.services.application_auth_service import revoke_application_auth_for_parent

        revoke_application_auth_for_parent(db, session.id, reason="USER_DISABLED")
        db.commit()
        return None
    session.last_activity_at = now
    session.expires_at = now + timedelta(minutes=auth_settings.idle_timeout_minutes)
    db.commit()
    return PortalSessionContext(session=session, user=user)


def get_user_for_session(db: Session, token: str | None) -> User | None:
    context = get_portal_session_context(db, token)
    return context.user if context else None


def revoke_session(db: Session, token: str | None, *, ip_address: str | None) -> None:
    if not token:
        return
    session = db.scalar(select(PortalSession).where(PortalSession.session_hash == hash_token(token)).with_for_update())
    if not session or session.revoked_at:
        return
    session.revoked_at = utcnow()
    from app.services.application_auth_service import revoke_application_auth_for_parent

    revoke_application_auth_for_parent(db, session.id, reason="PARENT_LOGOUT")
    write_audit(db, event_type="LOGOUT", result="SUCCESS", user_id=session.user_id, ip_address=ip_address)
    db.commit()


def revoke_user_auth_state(db: Session, user_id, *, include_password_resets: bool = True) -> None:
    now = utcnow()
    db.execute(
        update(PortalSession)
        .where(PortalSession.user_id == user_id, PortalSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    from app.services.application_auth_service import revoke_application_auth_for_user

    revoke_application_auth_for_user(db, user_id, reason="USER_SECURITY_RESET")
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
    if include_password_resets:
        db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .values(used_at=now)
        )

