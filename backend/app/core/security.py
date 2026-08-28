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


def generate_authorization_code() -> str:
    """Return an opaque code backed by exactly 256 bits of randomness."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    digest = hmac.new(settings.session_secret.encode(), token.encode(), hashlib.sha256).hexdigest()
    return digest


def hash_application_authorization_code(code: str) -> str:
    return _hash_scoped_token("application-authorization-code", code)


def hash_application_session_token(token: str) -> str:
    return _hash_scoped_token("application-session", token)


def _hash_scoped_token(purpose: str, token: str) -> str:
    payload = f"{purpose}\0{token}".encode()
    return hmac.new(settings.session_secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_application_client_secret(candidate: str) -> bool:
    expected = settings.opportunity_radar_client_secret
    if not expected:
        return False
    candidate_digest = hashlib.sha256(candidate.encode()).digest()
    expected_digest = hashlib.sha256(expected.encode()).digest()
    return hmac.compare_digest(candidate_digest, expected_digest)


def utcnow() -> datetime:
    return datetime.now(UTC)


def expires_in(seconds: int) -> datetime:
    return utcnow() + timedelta(seconds=seconds)

