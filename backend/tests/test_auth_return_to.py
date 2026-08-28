from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import Request, Response

from app.api.auth import login, logout, verify_mfa
from app.models.user import Role
from app.schemas.auth import EmailMfaVerifyRequest, LoginRequest
from app.schemas.user import CurrentUser


def http_request(cookies: dict[str, str] | None = None) -> Request:
    cookie_header = "; ".join(f"{key}={value}" for key, value in (cookies or {}).items()).encode()
    headers = [(b"user-agent", b"pytest")]
    if cookie_header:
        headers.append((b"cookie", cookie_header))
    return Request({
        "type": "http", "method": "POST", "path": "/api/auth/login", "headers": headers,
        "client": ("127.0.0.1", 12345), "server": ("testserver", 80), "scheme": "http",
        "query_string": b"", "root_path": "",
    })


def portal_user() -> SimpleNamespace:
    return SimpleNamespace(
        id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", username="assigned",
        email="assigned@example.com", display_name="Assigned User", role=Role.USER,
        mfa_enabled=False,
    )


def current_user() -> CurrentUser:
    return CurrentUser(
        id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", username="assigned",
        email="assigned@example.com", display_name="Assigned User", role=Role.USER,
        mfa_enabled=False, permissions=["applications.view", "applications.launch"],
    )


@patch("app.api.auth.current_user_payload", side_effect=lambda user, db: current_user())
@patch("app.api.auth.create_session_for_user")
@patch("app.api.auth.mfa_required_for_user", return_value=False)
@patch("app.api.auth.authenticate_password")
def test_password_login_returns_normalized_deep_link(authenticate, _mfa, create_session, _payload) -> None:
    user = portal_user()
    authenticate.return_value = user
    create_session.return_value = (user, "session-token", 1800)
    db = Mock()

    result = login(
        LoginRequest(
            identifier="assigned", password="correct-password",
            return_to="https://radar.blueashdigital.tech/jobs?tab=active",
        ),
        http_request(), Response(), db,
    )

    assert result.status == "AUTHENTICATED"
    assert result.return_to == "https://radar.blueashdigital.tech/jobs?tab=active"


@patch("app.api.auth.get_or_create_authentication_settings")
@patch("app.api.auth.send_email_mfa_code")
@patch("app.api.auth.create_pre_auth_session")
@patch("app.api.auth.mfa_required_for_user", return_value=True)
@patch("app.api.auth.authenticate_password")
def test_mfa_challenge_preserves_normalized_return_to(authenticate, _mfa, create_pre_auth, _send, settings) -> None:
    user = portal_user()
    authenticate.return_value = user
    now = datetime.now(UTC)
    pre_auth = SimpleNamespace(
        last_sent_at=now,
        expires_at=now + timedelta(minutes=10),
        return_to="https://radar.blueashdigital.tech/jobs",
    )
    create_pre_auth.return_value = (pre_auth, "pre-auth-token")
    settings.return_value = SimpleNamespace(mfa_code_expiration_minutes=10, mfa_resend_delay_seconds=60)

    result = login(
        LoginRequest(identifier="assigned", password="correct-password", return_to="/jobs"),
        http_request(), Response(), Mock(),
    )

    assert result.status == "MFA_REQUIRED"
    assert result.return_to == "https://radar.blueashdigital.tech/jobs"
    assert create_pre_auth.call_args.kwargs["return_to"] == "https://radar.blueashdigital.tech/jobs"


@patch("app.api.auth.current_user_payload", side_effect=lambda user, db: current_user())
@patch("app.api.auth.create_session_for_user")
@patch("app.api.auth.mfa_required_for_user", return_value=False)
@patch("app.api.auth.authenticate_password")
def test_invalid_return_to_falls_back_without_failing_login(authenticate, _mfa, create_session, _payload) -> None:
    user = portal_user()
    authenticate.return_value = user
    create_session.return_value = (user, "session-token", 1800)

    result = login(
        LoginRequest(identifier="assigned", password="correct-password", return_to="https://evil.example.com"),
        http_request(), Response(), Mock(),
    )

    assert result.status == "AUTHENTICATED"
    assert result.return_to is None


@patch("app.api.auth.current_user_payload", side_effect=lambda user, db: current_user())
@patch("app.api.auth.create_session_for_user")
@patch("app.api.auth.verify_email_mfa_code")
@patch("app.api.auth.get_pre_auth_session")
def test_valid_mfa_creates_host_only_session_cookie(get_pre_auth, verify_code, create_session, _payload) -> None:
    user = portal_user()
    get_pre_auth.return_value = SimpleNamespace(id="pre-auth", return_to="https://radar.blueashdigital.tech/")
    verify_code.return_value = user
    create_session.return_value = (user, "session-token", 1800)
    response = Response()

    result = verify_mfa(EmailMfaVerifyRequest(code="123456"), http_request(), response, Mock())

    assert result.user.email == "assigned@example.com"
    assert result.return_to == "https://radar.blueashdigital.tech/"
    set_cookies = response.headers.getlist("set-cookie")
    session_cookie = next(value for value in set_cookies if value.startswith("blueash_session="))
    assert "blueash_session=session-token" in session_cookie
    assert "HttpOnly" in session_cookie
    assert "Domain=" not in session_cookie
    assert "Path=/" in session_cookie


@patch("app.api.auth.revoke_session")
def test_logout_revokes_session_and_clears_host_only_cookie(revoke) -> None:
    response = Response()
    db = Mock()

    logout(http_request({"blueash_session": "session-token"}), response, db)

    revoke.assert_called_once_with(db, "session-token", ip_address="127.0.0.1")
    set_cookie = response.headers.get("set-cookie", "")
    assert "blueash_session=" in set_cookie
    assert "Max-Age=0" in set_cookie
