import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    digest = hmac.new(settings.session_secret.encode(), token.encode(), hashlib.sha256).hexdigest()
    return digest


def utcnow() -> datetime:
    return datetime.now(UTC)


def expires_in(seconds: int) -> datetime:
    return utcnow() + timedelta(seconds=seconds)

