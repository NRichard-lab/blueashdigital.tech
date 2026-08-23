from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.schemas.auth import LoginRequest, PasswordResetComplete, PasswordResetRequestCreate
from app.schemas.user import CurrentUser, current_user_payload
from app.services.email import EmailDeliveryError
from app.services.auth_service import authenticate, revoke_session
from app.services.password_reset_service import complete_password_reset, request_password_reset

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=CurrentUser)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> CurrentUser:
    result = authenticate(
        db,
        identifier=payload.identifier,
        password=payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password.")

    user, token = result
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        domain=settings.cookie_domain or None,
    )
    return current_user_payload(user, db)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    token = request.cookies.get(settings.session_cookie_name)
    revoke_session(db, token, ip_address=request.client.host if request.client else None)
    response.delete_cookie(settings.session_cookie_name, domain=settings.cookie_domain or None)
    return response


@router.post("/password-reset/request")
def request_reset(payload: PasswordResetRequestCreate, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        request_password_reset(db, identifier=payload.identifier, ip_address=request.client.host if request.client else None)
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.public_message) from exc
    return {"message": "If that account exists, password reset instructions have been sent."}


@router.post("/password-reset/complete")
def complete_reset(payload: PasswordResetComplete, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    if not complete_password_reset(db, token=payload.token, password=payload.password, ip_address=request.client.host if request.client else None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset link is invalid or expired.")
    return {"message": "Password has been reset."}
