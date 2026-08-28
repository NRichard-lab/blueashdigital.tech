from __future__ import annotations

import base64
import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    generate_authorization_code,
    generate_token,
    hash_application_authorization_code,
    hash_application_session_token,
    utcnow,
    verify_application_client_secret,
)
from app.models.application import Application, UserApplication
from app.models.application_auth import ApplicationAuthorizationCode, ApplicationSession
from app.models.session import PortalSession
from app.models.user import Role, User
from app.services.audit_service import write_audit
from app.services.authentication_settings_service import get_or_create_authentication_settings
from app.services.permission_service import get_user_permission_keys, user_has_permission


OPPORTUNITY_RADAR_SLUG = "opportunity-radar"
PKCE_CHALLENGE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")
PKCE_VERIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
STATE_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{20,256}$")


class ApplicationAuthError(Exception):
    pass


@dataclass(frozen=True)
class IssuedApplicationSession:
    token: str
    session: ApplicationSession


def validate_pkce_challenge(challenge: str, method: str) -> bool:
    return method == "S256" and bool(PKCE_CHALLENGE_PATTERN.fullmatch(challenge))


def validate_state(state: str) -> bool:
    return bool(STATE_PATTERN.fullmatch(state))


def verify_pkce(challenge: str, verifier: str) -> bool:
    if not PKCE_VERIFIER_PATTERN.fullmatch(verifier):
        return False
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    calculated = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(calculated, challenge)


def authenticate_application_client(client_id: str, client_secret: str) -> bool:
    expected_id = settings.opportunity_radar_client_id
    return hmac.compare_digest(client_id.encode(), expected_id.encode()) and verify_application_client_secret(client_secret)


def get_opportunity_radar(db: Session, *, lock: bool = False) -> Application | None:
    statement = select(Application).where(Application.slug == OPPORTUNITY_RADAR_SLUG)
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def has_explicit_application_assignment(db: Session, user_id, application_id) -> bool:
    assignment = db.scalar(
        select(UserApplication).where(
            UserApplication.user_id == user_id,
            UserApplication.application_id == application_id,
        )
    )
    return assignment is not None


def user_mfa_is_satisfied(user: User, parent_session: PortalSession) -> bool:
    requires_mfa = user.role == Role.ADMINISTRATOR or user.mfa_required
    return not requires_mfa or parent_session.mfa_satisfied_at is not None


def parent_session_is_active(parent_session: PortalSession, now) -> bool:
    return (
        parent_session.revoked_at is None
        and parent_session.expires_at > now
        and parent_session.absolute_expires_at > now
    )


def user_can_authorize_application(db: Session, user: User, parent_session: PortalSession, application: Application) -> bool:
    return (
        user.enabled
        and application.enabled
        and (user.role == Role.ADMINISTRATOR or not application.administrator_only)
        and parent_session_is_active(parent_session, utcnow())
        and user_mfa_is_satisfied(user, parent_session)
        and user_has_permission(db, user, "applications.launch")
        and has_explicit_application_assignment(db, user.id, application.id)
    )


def create_authorization_code(
    db: Session,
    *,
    user: User,
    parent_session: PortalSession,
    application: Application,
    callback_uri: str,
    pkce_challenge: str,
    return_path: str,
    ip_address: str | None,
) -> tuple[ApplicationAuthorizationCode, str]:
    now = utcnow()
    raw_code = generate_authorization_code()
    authorization_code = ApplicationAuthorizationCode(
        code_hash=hash_application_authorization_code(raw_code),
        user_id=user.id,
        parent_session_id=parent_session.id,
        application_id=application.id,
        callback_uri=callback_uri,
        pkce_challenge=pkce_challenge,
        return_path=return_path,
        expires_at=now + timedelta(seconds=settings.application_auth_code_ttl_seconds),
    )
    db.add(authorization_code)
    db.flush()
    write_audit(
        db,
        event_type="APPLICATION_AUTHORIZATION_INITIATED",
        result="SUCCESS",
        user_id=user.id,
        ip_address=ip_address,
        target_type="APPLICATION",
        target_id=str(application.id),
        metadata={"authorization_id": str(authorization_code.id)},
    )
    return authorization_code, raw_code


def exchange_authorization_code(
    db: Session,
    *,
    raw_code: str,
    code_verifier: str,
    redirect_uri: str,
    ip_address: str | None,
) -> IssuedApplicationSession:
    now = utcnow()
    candidate = db.scalar(
        select(ApplicationAuthorizationCode)
        .where(ApplicationAuthorizationCode.code_hash == hash_application_authorization_code(raw_code))
    )
    if not candidate:
        raise ApplicationAuthError("invalid_grant")
    parent_session = db.scalar(select(PortalSession).where(PortalSession.id == candidate.parent_session_id).with_for_update())
    if not parent_session:
        raise ApplicationAuthError("invalid_grant")
    code = db.scalar(
        select(ApplicationAuthorizationCode)
        .where(ApplicationAuthorizationCode.id == candidate.id)
        .with_for_update()
    )
    if not code or code.consumed_at or code.revoked_at or code.expires_at <= now:
        raise ApplicationAuthError("invalid_grant")
    if redirect_uri != settings.opportunity_radar_callback_uri or code.callback_uri != redirect_uri:
        raise ApplicationAuthError("invalid_grant")
    if not verify_pkce(code.pkce_challenge, code_verifier):
        raise ApplicationAuthError("invalid_grant")

    user = db.scalar(select(User).where(User.id == code.user_id).with_for_update())
    application = db.scalar(select(Application).where(Application.id == code.application_id).with_for_update())
    if not parent_session or not user or not application:
        raise ApplicationAuthError("invalid_grant")
    if parent_session.user_id != code.user_id:
        raise ApplicationAuthError("invalid_grant")
    if application.slug != OPPORTUNITY_RADAR_SLUG or not user_can_authorize_application(db, user, parent_session, application):
        code.revoked_at = now
        raise ApplicationAuthError("invalid_grant")

    code.consumed_at = now
    raw_token = generate_token()
    absolute_expires_at = min(
        parent_session.absolute_expires_at,
        now + timedelta(seconds=settings.application_session_absolute_max_seconds),
    )
    idle_expires_at = min(
        absolute_expires_at,
        now + timedelta(seconds=settings.application_session_idle_seconds),
    )
    if idle_expires_at <= now:
        raise ApplicationAuthError("invalid_grant")
    app_session = ApplicationSession(
        token_hash=hash_application_session_token(raw_token),
        user_id=user.id,
        parent_session_id=parent_session.id,
        application_id=application.id,
        last_seen_at=now,
        idle_expires_at=idle_expires_at,
        absolute_expires_at=absolute_expires_at,
    )
    db.add(app_session)
    db.flush()
    write_audit(
        db,
        event_type="APPLICATION_AUTHORIZATION_CODE_CONSUMED",
        result="SUCCESS",
        user_id=user.id,
        ip_address=ip_address,
        target_type="APPLICATION_SESSION",
        target_id=str(app_session.id),
        metadata={"authorization_id": str(code.id), "application_id": str(application.id)},
    )
    write_audit(
        db,
        event_type="APPLICATION_SESSION_CREATED",
        result="SUCCESS",
        user_id=user.id,
        ip_address=ip_address,
        target_type="APPLICATION_SESSION",
        target_id=str(app_session.id),
        metadata={"application_id": str(application.id)},
    )
    return IssuedApplicationSession(token=raw_token, session=app_session)


def introspect_application_session(db: Session, *, raw_token: str) -> dict:
    now = utcnow()
    candidate = db.scalar(
        select(ApplicationSession)
        .where(ApplicationSession.token_hash == hash_application_session_token(raw_token))
    )
    if not candidate:
        return {"active": False}
    parent_session = db.scalar(select(PortalSession).where(PortalSession.id == candidate.parent_session_id).with_for_update())
    if not parent_session:
        return {"active": False}
    app_session = db.scalar(select(ApplicationSession).where(ApplicationSession.id == candidate.id).with_for_update())
    if not app_session or app_session.revoked_at:
        return {"active": False}
    user = db.get(User, app_session.user_id)
    application = db.get(Application, app_session.application_id)
    active = (
        app_session.idle_expires_at > now
        and app_session.absolute_expires_at > now
        and parent_session.user_id == app_session.user_id
        and parent_session is not None
        and user is not None
        and application is not None
        and application.slug == OPPORTUNITY_RADAR_SLUG
        and user_can_authorize_application(db, user, parent_session, application)
    )
    if not active:
        app_session.revoked_at = now
        app_session.revocation_reason = "INTROSPECTION_REJECTED"
        db.flush()
        return {"active": False}

    auth_settings = get_or_create_authentication_settings(db)
    app_session.last_seen_at = now
    app_session.idle_expires_at = min(
        app_session.absolute_expires_at,
        now + timedelta(seconds=settings.application_session_idle_seconds),
    )
    parent_session.last_activity_at = now
    parent_session.expires_at = min(
        parent_session.absolute_expires_at,
        now + timedelta(minutes=auth_settings.idle_timeout_minutes),
    )
    permissions = sorted(get_user_permission_keys(db, user))
    db.flush()
    return {
        "active": True,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "permissions": permissions,
        "application_id": application.id,
        "application_slug": application.slug,
        "idle_expires_at": app_session.idle_expires_at,
        "absolute_expires_at": app_session.absolute_expires_at,
    }


def revoke_application_session(db: Session, *, raw_token: str, ip_address: str | None) -> None:
    now = utcnow()
    app_session = db.scalar(
        select(ApplicationSession)
        .where(ApplicationSession.token_hash == hash_application_session_token(raw_token))
        .with_for_update()
    )
    if not app_session or app_session.revoked_at:
        return
    application = db.get(Application, app_session.application_id)
    if not application or application.slug != OPPORTUNITY_RADAR_SLUG:
        return
    app_session.revoked_at = now
    app_session.revocation_reason = "APPLICATION_LOGOUT"
    write_audit(
        db,
        event_type="APPLICATION_SESSION_REVOKED",
        result="SUCCESS",
        user_id=app_session.user_id,
        ip_address=ip_address,
        target_type="APPLICATION_SESSION",
        target_id=str(app_session.id),
        metadata={"reason": "application_logout", "application_id": str(app_session.application_id)},
    )


def revoke_application_auth_for_parent(db: Session, parent_session_id, *, reason: str) -> None:
    now = utcnow()
    db.execute(
        update(ApplicationAuthorizationCode)
        .where(
            ApplicationAuthorizationCode.parent_session_id == parent_session_id,
            ApplicationAuthorizationCode.consumed_at.is_(None),
            ApplicationAuthorizationCode.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.execute(
        update(ApplicationSession)
        .where(ApplicationSession.parent_session_id == parent_session_id, ApplicationSession.revoked_at.is_(None))
        .values(revoked_at=now, revocation_reason=reason[:80])
    )


def revoke_application_auth_for_user(db: Session, user_id, *, reason: str, application_ids: set | None = None) -> None:
    now = utcnow()
    code_filters = [ApplicationAuthorizationCode.user_id == user_id, ApplicationAuthorizationCode.revoked_at.is_(None)]
    session_filters = [ApplicationSession.user_id == user_id, ApplicationSession.revoked_at.is_(None)]
    if application_ids is not None:
        if not application_ids:
            return
        code_filters.append(ApplicationAuthorizationCode.application_id.in_(application_ids))
        session_filters.append(ApplicationSession.application_id.in_(application_ids))
    db.execute(update(ApplicationAuthorizationCode).where(*code_filters).values(revoked_at=now))
    db.execute(update(ApplicationSession).where(*session_filters).values(revoked_at=now, revocation_reason=reason[:80]))


def cleanup_application_auth(db: Session, *, batch_size: int = 500) -> dict[str, int]:
    batch_size = max(1, min(batch_size, 5000))
    now = utcnow()
    retention_cutoff = now - timedelta(seconds=settings.application_auth_cleanup_retention_seconds)
    code_ids = (
        select(ApplicationAuthorizationCode.id)
        .where(
            or_(
                ApplicationAuthorizationCode.expires_at <= now,
                ApplicationAuthorizationCode.consumed_at <= retention_cutoff,
                ApplicationAuthorizationCode.revoked_at <= retention_cutoff,
            )
        )
        .order_by(ApplicationAuthorizationCode.expires_at)
        .limit(batch_size)
    )
    code_result = db.execute(delete(ApplicationAuthorizationCode).where(ApplicationAuthorizationCode.id.in_(code_ids)))
    session_ids = (
        select(ApplicationSession.id)
        .where(
            or_(
                ApplicationSession.idle_expires_at <= retention_cutoff,
                ApplicationSession.absolute_expires_at <= retention_cutoff,
                ApplicationSession.revoked_at <= retention_cutoff,
            )
        )
        .order_by(ApplicationSession.absolute_expires_at)
        .limit(batch_size)
    )
    session_result = db.execute(delete(ApplicationSession).where(ApplicationSession.id.in_(session_ids)))
    return {
        "authorization_codes_deleted": max(code_result.rowcount or 0, 0),
        "application_sessions_deleted": max(session_result.rowcount or 0, 0),
    }
