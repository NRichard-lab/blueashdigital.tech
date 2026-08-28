from fastapi import Response

from app.core.config import settings


LEGACY_SESSION_COOKIE_NAME = "blueash_session"
LEGACY_PRE_AUTH_COOKIE_NAME = "blueash_pre_auth"


def _clear_legacy_parent_cookie(response: Response, name: str) -> None:
    if not settings.is_production:
        return
    response.delete_cookie(
        name,
        path="/",
        domain=f".{settings.app_domain.lstrip('.')}",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def clear_legacy_parent_auth_cookies(response: Response) -> None:
    _clear_legacy_parent_cookie(response, LEGACY_SESSION_COOKIE_NAME)
    _clear_legacy_parent_cookie(response, LEGACY_PRE_AUTH_COOKIE_NAME)


def set_session_cookie(response: Response, token: str, max_age: int) -> None:
    _clear_legacy_parent_cookie(response, LEGACY_SESSION_COOKIE_NAME)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=max_age,
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )


def set_pre_auth_cookie(response: Response, token: str, max_age: int) -> None:
    _clear_legacy_parent_cookie(response, LEGACY_PRE_AUTH_COOKIE_NAME)
    response.set_cookie(
        settings.pre_auth_cookie_name,
        token,
        max_age=max_age,
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.is_production,
        httponly=True,
        samesite="lax",
    )
    _clear_legacy_parent_cookie(response, LEGACY_SESSION_COOKIE_NAME)


def clear_pre_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.pre_auth_cookie_name,
        path="/",
        secure=settings.is_production,
        httponly=True,
        samesite="lax",
    )
    _clear_legacy_parent_cookie(response, LEGACY_PRE_AUTH_COOKIE_NAME)
