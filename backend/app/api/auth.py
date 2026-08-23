from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import utcnow
from app.database.session import get_db
from app.schemas.auth import EmailMfaVerifyRequest, LoginRequest, LoginResponse, MfaRequiredResponse, PasswordResetComplete, PasswordResetRequestCreate
from app.schemas.user import CurrentUser, current_user_payload
from app.models.user import User
from app.services.email import EmailDeliveryError
from app.services.auth_service import authenticate_password, create_pre_auth_session, create_session_for_user, mfa_required_for_user, revoke_session
from app.services.authentication_settings_service import get_or_create_authentication_settings
from app.services.mfa_email_service import cancel_pre_auth_session, get_pre_auth_session, mask_email, send_email_mfa_code, verify_email_mfa_code
from app.services.password_reset_service import complete_password_reset, request_password_reset
from app.services.rate_limit_service import rate_limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        domain=settings.cookie_domain or None,
    )


def _set_pre_auth_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        settings.pre_auth_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        domain=settings.cookie_domain or None,
    )


def _clear_pre_auth_cookie(response: Response) -> None:
    response.delete_cookie(settings.pre_auth_cookie_name, domain=settings.cookie_domain or None)


def _mfa_response(pre_auth, user, auth_settings) -> MfaRequiredResponse:
    resend_available_at = pre_auth.last_sent_at + timedelta(seconds=auth_settings.mfa_resend_delay_seconds) if pre_auth.last_sent_at else None
    return MfaRequiredResponse(masked_email=mask_email(user.email), expires_at=pre_auth.expires_at, resend_available_at=resend_available_at)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    ip_address = request.client.host if request.client else "unknown"
    normalized = payload.identifier.strip().lower()
    if not rate_limiter.allow(f"login:{ip_address}:{normalized}", limit=8, window_seconds=300):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many sign-in attempts. Please wait and try again.")
    user = authenticate_password(
        db,
        identifier=payload.identifier,
        password=payload.password,
        ip_address=ip_address,
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password.")

    if mfa_required_for_user(user):
        auth_settings = get_or_create_authentication_settings(db)
        pre_auth, token = create_pre_auth_session(db, user=user, ip_address=ip_address, user_agent=request.headers.get("user-agent"))
        try:
            send_email_mfa_code(db, user=user, pre_auth_session=pre_auth, ip_address=ip_address)
        except EmailDeliveryError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.public_message) from exc
        db.commit()
        _set_pre_auth_cookie(response, token, auth_settings.mfa_code_expiration_minutes * 60)
        mfa_payload = _mfa_response(pre_auth, user, auth_settings)
        return LoginResponse(status="MFA_REQUIRED", masked_email=mfa_payload.masked_email, expires_at=mfa_payload.expires_at, resend_available_at=mfa_payload.resend_available_at)

    user, token, max_age = create_session_for_user(db, user=user, ip_address=ip_address, user_agent=request.headers.get("user-agent"))
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, token, max_age)
    return LoginResponse(status="AUTHENTICATED", user=current_user_payload(user, db))


@router.post("/mfa/verify", response_model=CurrentUser)
def verify_mfa(payload: EmailMfaVerifyRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> CurrentUser:
    ip_address = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"mfa-verify:{ip_address}", limit=15, window_seconds=300):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many verification attempts. Please wait and try again.")
    pre_auth = get_pre_auth_session(db, request.cookies.get(settings.pre_auth_cookie_name))
    if not pre_auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Verification session expired. Please sign in again.")
    user = verify_email_mfa_code(db, pre_auth_session=pre_auth, code=payload.code, ip_address=ip_address)
    if not user:
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired verification code.")
    user, token, max_age = create_session_for_user(db, user=user, ip_address=ip_address, user_agent=request.headers.get("user-agent"))
    db.commit()
    db.refresh(user)
    _clear_pre_auth_cookie(response)
    _set_session_cookie(response, token, max_age)
    return current_user_payload(user, db)


@router.post("/mfa/resend", response_model=MfaRequiredResponse)
def resend_mfa(request: Request, db: Session = Depends(get_db)) -> MfaRequiredResponse:
    ip_address = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"mfa-resend:{ip_address}", limit=5, window_seconds=300):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many code requests. Please wait and try again.")
    pre_auth = get_pre_auth_session(db, request.cookies.get(settings.pre_auth_cookie_name))
    if not pre_auth or pre_auth.completed_at or pre_auth.cancelled_at or pre_auth.expires_at <= utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Verification session expired. Please sign in again.")
    auth_settings = get_or_create_authentication_settings(db)
    user = db.get(User, pre_auth.user_id)
    if not user or not user.enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Verification session expired. Please sign in again.")
    if pre_auth.last_sent_at and pre_auth.last_sent_at + timedelta(seconds=auth_settings.mfa_resend_delay_seconds) > utcnow():
        return _mfa_response(pre_auth, user, auth_settings)
    try:
        send_email_mfa_code(db, user=user, pre_auth_session=pre_auth, ip_address=ip_address)
    except EmailDeliveryError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.public_message) from exc
    db.commit()
    return _mfa_response(pre_auth, user, auth_settings)


@router.post("/mfa/cancel", status_code=204)
def cancel_mfa(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    pre_auth = get_pre_auth_session(db, request.cookies.get(settings.pre_auth_cookie_name))
    if pre_auth:
        cancel_pre_auth_session(db, pre_auth_session=pre_auth, ip_address=request.client.host if request.client else None)
        db.commit()
    _clear_pre_auth_cookie(response)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    revoke_session(db, token, ip_address=request.client.host if request.client else None)
    response.delete_cookie(settings.session_cookie_name, domain=settings.cookie_domain or None)
    _clear_pre_auth_cookie(response)


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
