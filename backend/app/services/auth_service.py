from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import expires_in, generate_token, hash_token, utcnow, verify_password
from app.models.session import PortalSession
from app.models.user import User
from app.services.audit_service import write_audit


def authenticate(db: Session, *, identifier: str, password: str, ip_address: str | None, user_agent: str | None) -> tuple[User, str] | None:
    normalized = identifier.strip().lower()
    user = db.scalar(select(User).where(or_(User.username == normalized, User.email == normalized)))

    if not user or not user.enabled or not verify_password(password, user.password_hash):
        write_audit(db, event_type="LOGIN_FAILED", result="FAILURE", ip_address=ip_address, metadata={"identifier": normalized[:120]})
        db.commit()
        return None

    token = generate_token()
    session = PortalSession(
        user_id=user.id,
        session_hash=hash_token(token),
        ip_address=ip_address,
        user_agent=user_agent[:512] if user_agent else None,
        expires_at=expires_in(settings.session_max_age_seconds),
    )
    user.last_login_at = utcnow()
    db.add(session)
    write_audit(db, event_type="LOGIN_SUCCESSFUL", result="SUCCESS", user_id=user.id, ip_address=ip_address)
    db.commit()
    db.refresh(user)
    return user, token


def get_user_for_session(db: Session, token: str | None) -> User | None:
    if not token:
        return None

    session = db.scalar(select(PortalSession).where(PortalSession.session_hash == hash_token(token)))
    if not session or session.revoked_at or session.expires_at <= utcnow():
        return None

    user = db.get(User, session.user_id)
    if not user or not user.enabled:
        return None
    return user


def revoke_session(db: Session, token: str | None, *, ip_address: str | None) -> None:
    if not token:
        return
    session = db.scalar(select(PortalSession).where(PortalSession.session_hash == hash_token(token)))
    if not session or session.revoked_at:
        return
    session.revoked_at = utcnow()
    write_audit(db, event_type="LOGOUT", result="SUCCESS", user_id=session.user_id, ip_address=ip_address)
    db.commit()

