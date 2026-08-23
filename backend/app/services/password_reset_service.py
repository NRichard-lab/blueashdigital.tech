from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import expires_in, generate_token, hash_password, hash_token, utcnow
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.auth_service import revoke_user_auth_state
from app.services.audit_service import write_audit
from app.services.email import EmailDeliveryError, send_configured_email
from app.services.email.templates import password_reset_email

RESET_TOKEN_TTL_SECONDS = 60 * 30


def request_password_reset(db: Session, *, identifier: str, ip_address: str | None) -> None:
    normalized = identifier.strip().lower()
    user = db.scalar(select(User).where(or_(User.username == normalized, User.email == normalized)))
    if not user or not user.enabled:
        write_audit(db, event_type="PASSWORD_RESET_REQUESTED", result="SUCCESS", ip_address=ip_address, metadata={"matched": False})
        db.commit()
        return

    token = generate_token()
    db.execute(update(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)).values(used_at=utcnow()))
    reset = PasswordResetToken(user_id=user.id, token_hash=hash_token(token), expires_at=expires_in(RESET_TOKEN_TTL_SECONDS))
    db.add(reset)
    reset_url = f"{settings.frontend_origin.rstrip('/')}/reset-password?token={token}"
    send_configured_email(db, password_reset_email(to=user.email, reset_url=reset_url, expires_minutes=RESET_TOKEN_TTL_SECONDS // 60))
    write_audit(db, event_type="PASSWORD_RESET_REQUESTED", result="SUCCESS", user_id=user.id, ip_address=ip_address)
    db.commit()


def complete_password_reset(db: Session, *, token: str, password: str, ip_address: str | None) -> bool:
    reset = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token)))
    if not reset or reset.used_at or reset.expires_at <= utcnow():
        write_audit(db, event_type="PASSWORD_RESET_COMPLETED", result="FAILURE", ip_address=ip_address)
        db.commit()
        return False
    user = db.get(User, reset.user_id)
    if not user or not user.enabled:
        write_audit(db, event_type="PASSWORD_RESET_COMPLETED", result="FAILURE", ip_address=ip_address)
        db.commit()
        return False
    user.password_hash = hash_password(password)
    user.force_password_change = False
    reset.used_at = utcnow()
    revoke_user_auth_state(db, user.id, include_password_resets=False)
    write_audit(db, event_type="PASSWORD_RESET_COMPLETED", result="SUCCESS", user_id=user.id, ip_address=ip_address)
    db.commit()
    return True
