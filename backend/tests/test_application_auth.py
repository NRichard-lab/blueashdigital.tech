import base64
import hashlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch
import uuid

import pytest
from fastapi import Request

from app.api.application_auth import authorize
from app.core.config import Settings
from app.core.cookies import clear_legacy_parent_auth_cookies, set_session_cookie
from app.core.security import hash_application_authorization_code, hash_application_session_token
from app.models.application import Application, ApplicationStatus, ApplicationType
from app.models.application_auth import ApplicationAuthorizationCode, ApplicationSession
from app.models.session import PortalSession
from app.models.user import Role, User
from app.services.application_auth_service import (
    ApplicationAuthError,
    authenticate_application_client,
    exchange_authorization_code,
    introspect_application_session,
    revoke_application_session,
    user_can_authorize_application,
    validate_pkce_challenge,
    verify_pkce,
)
from app.services.auth_service import revoke_session
from starlette.responses import Response


RADAR_ID = uuid.UUID("6f742cd7-5090-4cb2-8c35-8d9644e9ab5e")
USER_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
SESSION_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
CALLBACK = "https://radar.blueashdigital.tech/api/auth/callback"


def pkce_pair() -> tuple[str, str]:
    verifier = "v" * 64
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def radar_application(*, enabled: bool = True, administrator_only: bool = False) -> Application:
    return Application(
        id=RADAR_ID,
        name="Opportunity Radar",
        slug="opportunity-radar",
        description="Radar",
        icon="RADAR",
        category="Career Tools",
        application_type=ApplicationType.INTERNAL_WEB,
        launch_url="https://radar.blueashdigital.tech/",
        enabled=enabled,
        administrator_only=administrator_only,
        display_order=20,
        status=ApplicationStatus.UNKNOWN,
    )


def portal_user(*, role: Role = Role.USER, enabled: bool = True) -> User:
    return User(
        id=USER_ID,
        username="assigned",
        email="assigned@example.com",
        display_name="Assigned User",
        password_hash="unused",
        role=role,
        enabled=enabled,
        mfa_required=role == Role.ADMINISTRATOR,
    )


def portal_session(now: datetime, *, mfa: bool = False) -> PortalSession:
    return PortalSession(
        id=SESSION_ID,
        user_id=USER_ID,
        session_hash="portal-hash",
        last_activity_at=now,
        mfa_satisfied_at=now if mfa else None,
        expires_at=now + timedelta(hours=1),
        absolute_expires_at=now + timedelta(hours=4),
    )


def request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/app-auth/authorize",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "https",
            "query_string": b"",
            "root_path": "",
        }
    )


def test_s256_pkce_is_exact_and_verifier_is_checked() -> None:
    verifier, challenge = pkce_pair()
    assert len(challenge) == 43
    assert validate_pkce_challenge(challenge, "S256")
    assert not validate_pkce_challenge(f"{challenge}a", "S256")
    assert not validate_pkce_challenge(challenge, "plain")
    assert verify_pkce(challenge, verifier)
    assert not verify_pkce(challenge, "x" * 64)


def test_application_client_credentials_are_exact_and_fail_closed() -> None:
    with patch("app.services.application_auth_service.settings.opportunity_radar_client_id", "opportunity-radar"), patch(
        "app.core.security.settings.opportunity_radar_client_secret", "client-secret-with-at-least-thirty-two-bytes"
    ):
        assert authenticate_application_client("opportunity-radar", "client-secret-with-at-least-thirty-two-bytes")
        assert not authenticate_application_client("wrong-client", "client-secret-with-at-least-thirty-two-bytes")
        assert not authenticate_application_client("opportunity-radar", "wrong-secret")
    with patch("app.core.security.settings.opportunity_radar_client_secret", None):
        assert not authenticate_application_client("opportunity-radar", "anything")


@patch("app.services.application_auth_service.user_has_permission", return_value=True)
def test_application_handoff_requires_explicit_assignment_for_admin_and_user(_permission) -> None:
    now = datetime.now(UTC)
    application = radar_application()
    for role in (Role.USER, Role.ADMINISTRATOR):
        user = portal_user(role=role)
        parent = portal_session(now, mfa=role == Role.ADMINISTRATOR)
        db = Mock()
        db.scalar.return_value = None
        assert not user_can_authorize_application(db, user, parent, application)
        db.scalar.return_value = SimpleNamespace(user_id=user.id, application_id=application.id)
        assert user_can_authorize_application(db, user, parent, application)


@patch("app.services.application_auth_service.user_has_permission", return_value=True)
def test_application_authorization_rechecks_user_app_parent_mfa_and_admin_only(_permission) -> None:
    now = datetime.now(UTC)
    assignment = SimpleNamespace(user_id=USER_ID, application_id=RADAR_ID)
    db = Mock()
    db.scalar.return_value = assignment
    assert not user_can_authorize_application(db, portal_user(enabled=False), portal_session(now), radar_application())
    assert not user_can_authorize_application(db, portal_user(), portal_session(now), radar_application(enabled=False))
    expired_parent = portal_session(now)
    expired_parent.expires_at = now - timedelta(seconds=1)
    assert not user_can_authorize_application(db, portal_user(), expired_parent, radar_application())
    revoked_parent = portal_session(now)
    revoked_parent.revoked_at = now
    assert not user_can_authorize_application(db, portal_user(), revoked_parent, radar_application())
    assert not user_can_authorize_application(db, portal_user(), portal_session(now), radar_application(administrator_only=True))
    assert not user_can_authorize_application(db, portal_user(role=Role.ADMINISTRATOR), portal_session(now), radar_application())
    assert user_can_authorize_application(
        db,
        portal_user(role=Role.ADMINISTRATOR),
        portal_session(now, mfa=True),
        radar_application(administrator_only=True),
    )


@patch("app.services.application_auth_service.user_can_authorize_application", return_value=True)
def test_exchange_consumes_code_once_and_bounds_child_absolute_expiry(_authorized) -> None:
    now = datetime.now(UTC)
    verifier, challenge = pkce_pair()
    raw_code = "authorization-code-value"
    code = ApplicationAuthorizationCode(
        id=uuid.uuid4(),
        code_hash=hash_application_authorization_code(raw_code),
        user_id=USER_ID,
        parent_session_id=SESSION_ID,
        application_id=RADAR_ID,
        callback_uri=CALLBACK,
        pkce_challenge=challenge,
        return_path="/jobs",
        created_at=now,
        expires_at=now + timedelta(seconds=60),
    )
    parent = portal_session(now)
    user = portal_user()
    application = radar_application()
    db = Mock()
    db.scalar.side_effect = [code, parent, code, user, application]

    issued = exchange_authorization_code(
        db,
        raw_code=raw_code,
        code_verifier=verifier,
        redirect_uri=CALLBACK,
        ip_address="127.0.0.1",
    )

    assert code.consumed_at is not None
    assert issued.session.absolute_expires_at <= parent.absolute_expires_at
    assert issued.session.token_hash == hash_application_session_token(issued.token)
    assert issued.session.token_hash != issued.token
    db.scalar.side_effect = [code, parent, code]
    with pytest.raises(ApplicationAuthError):
        exchange_authorization_code(
            db,
            raw_code=raw_code,
            code_verifier=verifier,
            redirect_uri=CALLBACK,
            ip_address="127.0.0.1",
        )


@pytest.mark.parametrize("failure", ["expired", "pkce", "callback", "authorization"])
def test_exchange_rejects_expiry_pkce_callback_and_changed_authorization(failure: str) -> None:
    now = datetime.now(UTC)
    verifier, challenge = pkce_pair()
    raw_code = "authorization-code-value"
    code = ApplicationAuthorizationCode(
        id=uuid.uuid4(),
        code_hash=hash_application_authorization_code(raw_code),
        user_id=USER_ID,
        parent_session_id=SESSION_ID,
        application_id=RADAR_ID,
        callback_uri=CALLBACK,
        pkce_challenge=challenge,
        return_path="/",
        created_at=now,
        expires_at=now - timedelta(seconds=1) if failure == "expired" else now + timedelta(seconds=60),
    )
    db = Mock()
    db.scalar.side_effect = [code, portal_session(now), code, portal_user(), radar_application()]
    with patch("app.services.application_auth_service.user_can_authorize_application", return_value=failure != "authorization"):
        with pytest.raises(ApplicationAuthError):
            exchange_authorization_code(
                db,
                raw_code=raw_code,
                code_verifier="x" * 64 if failure == "pkce" else verifier,
                redirect_uri="https://radar.blueashdigital.tech/wrong" if failure == "callback" else CALLBACK,
                ip_address="127.0.0.1",
            )
    assert code.consumed_at is None
    if failure == "authorization":
        assert code.revoked_at is not None


def test_exchange_rejects_unknown_or_modified_code_generically() -> None:
    db = Mock()
    db.scalar.return_value = None
    with pytest.raises(ApplicationAuthError, match="invalid_grant"):
        exchange_authorization_code(
            db,
            raw_code="modified-or-unknown-authorization-code",
            code_verifier="v" * 64,
            redirect_uri=CALLBACK,
            ip_address="127.0.0.1",
        )
    db.add.assert_not_called()


@pytest.mark.parametrize("change", ["assignment_removed", "user_disabled", "application_disabled", "wrong_audience"])
@patch("app.services.application_auth_service.user_has_permission", return_value=True)
def test_exchange_rechecks_distinct_authorization_changes(_permission, change: str) -> None:
    now = datetime.now(UTC)
    verifier, challenge = pkce_pair()
    code = ApplicationAuthorizationCode(
        id=uuid.uuid4(),
        code_hash=hash_application_authorization_code("authorization-code-value"),
        user_id=USER_ID,
        parent_session_id=SESSION_ID,
        application_id=RADAR_ID,
        callback_uri=CALLBACK,
        pkce_challenge=challenge,
        return_path="/",
        created_at=now,
        expires_at=now + timedelta(seconds=60),
    )
    user = portal_user(enabled=change != "user_disabled")
    application = radar_application(enabled=change != "application_disabled")
    if change == "wrong_audience":
        application.slug = "another-application"
    scalar_results = [code, portal_session(now), code, user, application]
    if change == "assignment_removed":
        scalar_results.append(None)
    db = Mock()
    db.scalar.side_effect = scalar_results

    with pytest.raises(ApplicationAuthError, match="invalid_grant"):
        exchange_authorization_code(
            db,
            raw_code="authorization-code-value",
            code_verifier=verifier,
            redirect_uri=CALLBACK,
            ip_address="127.0.0.1",
        )
    assert code.consumed_at is None
    assert code.revoked_at is not None


def test_exchange_rejects_code_not_bound_to_parent_session_user() -> None:
    now = datetime.now(UTC)
    verifier, challenge = pkce_pair()
    code = ApplicationAuthorizationCode(
        id=uuid.uuid4(),
        code_hash=hash_application_authorization_code("authorization-code-value"),
        user_id=USER_ID,
        parent_session_id=SESSION_ID,
        application_id=RADAR_ID,
        callback_uri=CALLBACK,
        pkce_challenge=challenge,
        return_path="/",
        created_at=now,
        expires_at=now + timedelta(seconds=60),
    )
    wrong_parent = portal_session(now)
    wrong_parent.user_id = uuid.UUID("99999999-9999-4999-8999-999999999999")
    db = Mock()
    db.scalar.side_effect = [code, wrong_parent, code, portal_user(), radar_application()]

    with pytest.raises(ApplicationAuthError, match="invalid_grant"):
        exchange_authorization_code(
            db,
            raw_code="authorization-code-value",
            code_verifier=verifier,
            redirect_uri=CALLBACK,
            ip_address="127.0.0.1",
        )
    assert code.consumed_at is None


@patch("app.services.application_auth_service.get_user_permission_keys", return_value={"applications.launch"})
@patch("app.services.application_auth_service.get_or_create_authentication_settings", return_value=SimpleNamespace(idle_timeout_minutes=30))
@patch("app.services.application_auth_service.user_can_authorize_application", return_value=True)
def test_introspection_extends_idle_but_not_absolute(_authorized, _auth_settings, _permissions) -> None:
    now = datetime.now(UTC)
    parent = portal_session(now)
    app_session = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=USER_ID,
        parent_session_id=SESSION_ID,
        application_id=RADAR_ID,
        revoked_at=None,
        last_seen_at=now - timedelta(minutes=10),
        idle_expires_at=now + timedelta(minutes=20),
        absolute_expires_at=now + timedelta(hours=2),
        revocation_reason=None,
    )
    db = Mock()
    db.scalar.side_effect = [app_session, parent, app_session]
    db.get.side_effect = [portal_user(), radar_application()]
    result = introspect_application_session(db, raw_token="opaque-application-session-token")
    assert result["active"] is True
    assert app_session.last_seen_at >= now
    assert app_session.idle_expires_at <= app_session.absolute_expires_at
    assert parent.expires_at <= parent.absolute_expires_at


@patch("app.services.application_auth_service.user_can_authorize_application", return_value=False)
def test_introspection_revokes_session_after_assignment_user_app_or_parent_change(_authorized) -> None:
    now = datetime.now(UTC)
    app_session = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=USER_ID,
        parent_session_id=SESSION_ID,
        application_id=RADAR_ID,
        revoked_at=None,
        last_seen_at=now,
        idle_expires_at=now + timedelta(minutes=30),
        absolute_expires_at=now + timedelta(hours=2),
        revocation_reason=None,
    )
    db = Mock()
    db.scalar.side_effect = [app_session, portal_session(now), app_session]
    db.get.side_effect = [portal_user(), radar_application()]
    assert introspect_application_session(db, raw_token="opaque-application-session-token") == {"active": False}
    assert app_session.revoked_at is not None
    assert app_session.revocation_reason == "INTROSPECTION_REJECTED"


@pytest.mark.parametrize("expiry", ["idle", "absolute"])
@patch("app.services.application_auth_service.user_can_authorize_application", return_value=True)
def test_introspection_rejects_expired_application_session(_authorized, expiry: str) -> None:
    now = datetime.now(UTC)
    app_session = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=USER_ID,
        parent_session_id=SESSION_ID,
        application_id=RADAR_ID,
        revoked_at=None,
        last_seen_at=now - timedelta(minutes=31),
        idle_expires_at=now - timedelta(seconds=1) if expiry == "idle" else now + timedelta(minutes=10),
        absolute_expires_at=now - timedelta(seconds=1) if expiry == "absolute" else now + timedelta(hours=1),
        revocation_reason=None,
    )
    db = Mock()
    db.scalar.side_effect = [app_session, portal_session(now), app_session]
    db.get.side_effect = [portal_user(), radar_application()]

    assert introspect_application_session(db, raw_token="opaque-application-session-token") == {"active": False}
    assert app_session.revoked_at is not None
    assert app_session.revocation_reason == "INTROSPECTION_REJECTED"


def test_introspection_rejects_revoked_or_cross_user_application_session() -> None:
    now = datetime.now(UTC)
    revoked = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=USER_ID,
        parent_session_id=SESSION_ID,
        application_id=RADAR_ID,
        revoked_at=now,
        idle_expires_at=now + timedelta(minutes=10),
        absolute_expires_at=now + timedelta(hours=1),
    )
    db = Mock()
    db.scalar.side_effect = [revoked, portal_session(now), revoked]
    assert introspect_application_session(db, raw_token="revoked-application-session-token") == {"active": False}

    cross_user = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=USER_ID,
        parent_session_id=SESSION_ID,
        application_id=RADAR_ID,
        revoked_at=None,
        last_seen_at=now,
        idle_expires_at=now + timedelta(minutes=10),
        absolute_expires_at=now + timedelta(hours=1),
        revocation_reason=None,
    )
    wrong_parent = portal_session(now)
    wrong_parent.user_id = uuid.UUID("99999999-9999-4999-8999-999999999999")
    db = Mock()
    db.scalar.side_effect = [cross_user, wrong_parent, cross_user]
    db.get.side_effect = [portal_user(), radar_application()]
    assert introspect_application_session(db, raw_token="cross-user-application-session-token") == {"active": False}
    assert cross_user.revoked_at is not None


def test_revoke_application_session_is_idempotent_and_scoped_to_radar() -> None:
    now = datetime.now(UTC)
    app_session = ApplicationSession(
        id=uuid.uuid4(),
        token_hash=hash_application_session_token("opaque-application-session-token"),
        user_id=USER_ID,
        parent_session_id=SESSION_ID,
        application_id=RADAR_ID,
        created_at=now,
        last_seen_at=now,
        idle_expires_at=now + timedelta(minutes=30),
        absolute_expires_at=now + timedelta(hours=2),
    )
    db = Mock()
    db.scalar.return_value = app_session
    db.get.return_value = radar_application()
    revoke_application_session(db, raw_token="opaque-application-session-token", ip_address="127.0.0.1")
    assert app_session.revoked_at is not None
    assert app_session.revocation_reason == "APPLICATION_LOGOUT"

    first_revoked_at = app_session.revoked_at
    revoke_application_session(db, raw_token="opaque-application-session-token", ip_address="127.0.0.1")
    assert app_session.revoked_at == first_revoked_at


@patch("app.services.application_auth_service.revoke_application_auth_for_parent")
def test_parent_logout_revokes_child_codes_and_sessions(revoke_children) -> None:
    now = datetime.now(UTC)
    parent = portal_session(now)
    db = Mock()
    db.scalar.return_value = parent
    with patch("app.services.auth_service.hash_token", return_value="portal-hash"):
        revoke_session(db, "raw-parent-token", ip_address="127.0.0.1")
    assert parent.revoked_at is not None
    revoke_children.assert_called_once_with(db, parent.id, reason="PARENT_LOGOUT")
    db.commit.assert_called_once()


@patch("app.api.application_auth.get_portal_session_context", return_value=None)
def test_authorize_without_portal_session_redirects_to_login_with_safe_radar_ui(_context) -> None:
    _, challenge = pkce_pair()
    response = authorize(
        request(),
        client_id="opportunity-radar",
        redirect_uri=CALLBACK,
        response_type="code",
        state_value="s" * 43,
        code_challenge=challenge,
        code_challenge_method="S256",
        return_path="/jobs",
        db=Mock(),
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("http://localhost:5173/?returnTo=")
    assert "%2Fapi%2F" not in response.headers["location"]


@patch("app.api.application_auth.get_opportunity_radar")
@patch("app.api.application_auth.user_can_authorize_application", return_value=False)
@patch("app.api.application_auth.user_mfa_is_satisfied", return_value=True)
@patch("app.api.application_auth.get_portal_session_context")
def test_authorize_denial_returns_error_to_exact_callback(context, _mfa, _allowed, get_app) -> None:
    now = datetime.now(UTC)
    context.return_value = SimpleNamespace(user=portal_user(), session=portal_session(now))
    get_app.return_value = radar_application()
    _, challenge = pkce_pair()
    response = authorize(
        request(),
        client_id="opportunity-radar",
        redirect_uri=CALLBACK,
        response_type="code",
        state_value="s" * 43,
        code_challenge=challenge,
        code_challenge_method="S256",
        return_path="/",
        db=Mock(),
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"{CALLBACK}?error=access_denied&state={'s' * 43}"


def test_production_application_auth_config_is_fail_closed() -> None:
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            app_env="production",
            session_cookie_name="__Host-blueash_portal_session",
            pre_auth_cookie_name="__Host-blueash_pre_auth",
            opportunity_radar_client_secret=None,
        )
    config = Settings(
        _env_file=None,
        app_env="production",
        session_cookie_name="__Host-blueash_portal_session",
        pre_auth_cookie_name="__Host-blueash_pre_auth",
        opportunity_radar_client_secret="x" * 48,
    )
    assert config.application_auth_code_ttl_seconds == 60
    assert config.application_session_idle_seconds == 1800
    with pytest.raises(ValueError):
        Settings(_env_file=None, application_auth_code_ttl_seconds=0)


def test_production_cookie_is_host_only_and_legacy_parent_cookie_is_expired() -> None:
    response = Response()
    production = SimpleNamespace(
        is_production=True,
        app_domain="blueashdigital.tech",
        session_cookie_name="__Host-blueash_portal_session",
        pre_auth_cookie_name="__Host-blueash_pre_auth",
    )
    with patch("app.core.cookies.settings", production):
        set_session_cookie(response, "opaque", 1800)
        clear_legacy_parent_auth_cookies(response)
    headers = response.headers.getlist("set-cookie")
    active = next(value for value in headers if value.startswith("__Host-blueash_portal_session=opaque"))
    assert "Secure" in active and "HttpOnly" in active and "SameSite=lax" in active and "Path=/" in active
    assert "Domain=" not in active
    assert any(value.startswith("blueash_session=") and "Domain=.blueashdigital.tech" in value for value in headers)
