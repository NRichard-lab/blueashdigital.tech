from collections.abc import Callable

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models.user import Role, User
from app.services.auth_service import get_user_for_session
from app.services.permission_service import user_has_permission


def current_user(
    request: Request,
    db: Session = Depends(get_db),
    cookie_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> User:
    user = get_user_for_session(db, cookie_token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session has expired. Please sign in again.")
    request.state.user = user
    return user


def administrator(user: User = Depends(current_user)) -> User:
    if user.role != Role.ADMINISTRATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required.")
    return user


def require_permission(permission_key: str) -> Callable[[Request, User, Session], User]:
    def dependency(
        request: Request,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not user_has_permission(db, user, permission_key):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission required.")
        request.state.permission = permission_key
        return user

    return dependency

