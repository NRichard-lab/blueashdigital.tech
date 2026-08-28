from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cookies import clear_session_cookie
from app.core.redirects import normalize_radar_return_path, radar_return_url
from app.database.session import get_db
from app.schemas.application_auth import (
    ApplicationIntrospectionResponse,
    ApplicationTokenExchangeRequest,
    ApplicationTokenExchangeResponse,
    ApplicationTokenRequest,
)
from app.services.application_auth_service import (
    ApplicationAuthError,
    authenticate_application_client,
    cleanup_application_auth,
    create_authorization_code,
    exchange_authorization_code,
    get_opportunity_radar,
    introspect_application_session,
    revoke_application_session,
    user_can_authorize_application,
    user_mfa_is_satisfied,
    validate_pkce_challenge,
    validate_state,
)
from app.services.audit_service import write_audit
from app.services.auth_service import get_portal_session_context, revoke_session


router = APIRouter(prefix="/api/app-auth", tags=["application-auth"])
basic_auth = HTTPBasic(auto_error=False)


def _client_credentials(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(basic_auth)],
) -> str:
    if (
        not credentials
        or len(credentials.username) > 120
        or len(credentials.password) > 512
        or not authenticate_application_client(credentials.username, credentials.password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid application client credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _login_redirect(return_path: str) -> RedirectResponse:
    query = urlencode({"returnTo": radar_return_url(return_path)})
    separator = "&" if "?" in settings.frontend_origin else "?"
    response = RedirectResponse(f"{settings.frontend_origin.rstrip('/')}/{separator}{query}", status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookie(response)
    _no_store(response)
    return response


def _callback_redirect(redirect_uri: str, **parameters: str) -> RedirectResponse:
    response = RedirectResponse(f"{redirect_uri}?{urlencode(parameters)}", status_code=status.HTTP_303_SEE_OTHER)
    response.headers["Referrer-Policy"] = "no-referrer"
    _no_store(response)
    return response


@router.get("/authorize")
def authorize(
    request: Request,
    client_id: str = Query(min_length=1, max_length=120),
    redirect_uri: str = Query(min_length=1, max_length=2048),
    response_type: str = Query(min_length=1, max_length=20),
    state_value: str = Query(alias="state", min_length=20, max_length=256),
    code_challenge: str = Query(min_length=43, max_length=128),
    code_challenge_method: str = Query(min_length=1, max_length=20),
    return_path: str = Query(default="/", min_length=1, max_length=2048),
    db: Session = Depends(get_db),
) -> Response:
    safe_return_path = normalize_radar_return_path(return_path)
    valid_request = (
        client_id == settings.opportunity_radar_client_id
        and redirect_uri == settings.opportunity_radar_callback_uri
        and response_type == "code"
        and validate_state(state_value)
        and validate_pkce_challenge(code_challenge, code_challenge_method)
        and safe_return_path is not None
    )
    if not valid_request:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application authorization request.")

    portal_token = request.cookies.get(settings.session_cookie_name)
    context = get_portal_session_context(db, portal_token)
    if not context:
        return _login_redirect(safe_return_path)
    if not user_mfa_is_satisfied(context.user, context.session):
        revoke_session(db, portal_token, ip_address=request.client.host if request.client else None)
        return _login_redirect(safe_return_path)

    application = get_opportunity_radar(db, lock=True)
    if not application or not user_can_authorize_application(db, context.user, context.session, application):
        write_audit(
            db,
            event_type="APPLICATION_AUTHORIZATION_DENIED",
            result="FAILURE",
            user_id=context.user.id,
            ip_address=request.client.host if request.client else None,
            target_type="APPLICATION",
            target_id=str(application.id) if application else None,
        )
        db.commit()
        return _callback_redirect(redirect_uri, error="access_denied", state=state_value)

    cleanup_application_auth(db, batch_size=100)
    _, raw_code = create_authorization_code(
        db,
        user=context.user,
        parent_session=context.session,
        application=application,
        callback_uri=redirect_uri,
        pkce_challenge=code_challenge,
        return_path=safe_return_path,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return _callback_redirect(redirect_uri, code=raw_code, state=state_value)


@router.post("/exchange", response_model=ApplicationTokenExchangeResponse)
def exchange(
    payload: ApplicationTokenExchangeRequest,
    request: Request,
    response: Response,
    _: str = Depends(_client_credentials),
    db: Session = Depends(get_db),
) -> ApplicationTokenExchangeResponse:
    _no_store(response)
    cleanup_application_auth(db, batch_size=100)
    try:
        issued = exchange_authorization_code(
            db,
            raw_code=payload.code,
            code_verifier=payload.code_verifier,
            redirect_uri=payload.redirect_uri,
            ip_address=request.client.host if request.client else None,
        )
    except ApplicationAuthError as exc:
        write_audit(
            db,
            event_type="APPLICATION_AUTHORIZATION_EXCHANGE_REJECTED",
            result="FAILURE",
            ip_address=request.client.host if request.client else None,
            target_type="APPLICATION",
            metadata={"reason": "invalid_grant"},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired authorization grant.") from exc
    db.commit()
    app_session = issued.session
    expires_in = max(0, int((app_session.absolute_expires_at - app_session.last_seen_at).total_seconds()))
    return ApplicationTokenExchangeResponse(
        access_token=issued.token,
        expires_in=expires_in,
        idle_expires_at=app_session.idle_expires_at,
        absolute_expires_at=app_session.absolute_expires_at,
    )


@router.post("/introspect", response_model=ApplicationIntrospectionResponse, response_model_exclude_none=True)
def introspect(
    payload: ApplicationTokenRequest,
    request: Request,
    response: Response,
    _: str = Depends(_client_credentials),
    db: Session = Depends(get_db),
) -> ApplicationIntrospectionResponse:
    _no_store(response)
    result = introspect_application_session(db, raw_token=payload.token)
    if not result["active"]:
        write_audit(
            db,
            event_type="APPLICATION_INTROSPECTION_REJECTED",
            result="FAILURE",
            ip_address=request.client.host if request.client else None,
            target_type="APPLICATION",
        )
    db.commit()
    return ApplicationIntrospectionResponse(**result)


@router.post("/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke(
    payload: ApplicationTokenRequest,
    request: Request,
    response: Response,
    _: str = Depends(_client_credentials),
    db: Session = Depends(get_db),
) -> None:
    _no_store(response)
    revoke_application_session(db, raw_token=payload.token, ip_address=request.client.host if request.client else None)
    db.commit()
