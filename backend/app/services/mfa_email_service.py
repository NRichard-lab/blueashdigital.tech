import secrets

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import expires_in, hash_token, utcnow
from app.models.email_settings import EmailMfaChallenge
from app.models.user import User
from app.services.email import send_configured_email
from app.services.email.templates import email_mfa_code

EMAIL_MFA_TTL_SECONDS = 60 * 10
MAX_ATTEMPTS = 5


def send_email_mfa_code(db: Session, *, user: User, ip_address: str | None) -> None:
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.execute(delete(EmailMfaChallenge).where(EmailMfaChallenge.user_id == user.id, EmailMfaChallenge.used_at.is_(None)))
    db.add(EmailMfaChallenge(user_id=user.id, code_hash=hash_token(code), expires_at=expires_in(EMAIL_MFA_TTL_SECONDS), ip_address=ip_address))
    send_configured_email(db, email_mfa_code(to=user.email, code=code, expires_minutes=EMAIL_MFA_TTL_SECONDS // 60))
    db.commit()


def verify_email_mfa_code(db: Session, *, user: User, code: str) -> bool:
    challenge = db.scalar(
        select(EmailMfaChallenge)
        .where(EmailMfaChallenge.user_id == user.id, EmailMfaChallenge.used_at.is_(None))
        .order_by(EmailMfaChallenge.created_at.desc())
        .limit(1)
    )
    if not challenge or challenge.expires_at <= utcnow() or challenge.attempts >= MAX_ATTEMPTS:
        return False
    challenge.attempts += 1
    if challenge.code_hash != hash_token(code):
        db.commit()
        return False
    challenge.used_at = utcnow()
    db.commit()
    return True
