from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.secrets import encrypt_secret
from app.core.security import utcnow
from app.database.session import get_db
from app.models.email_settings import EmailSettings, EmailStatus
from app.models.role import PortalPermission, PortalRole, RolePermission
from app.models.user import User
from app.schemas.settings import EmailSettingsRead, EmailSettingsUpdate, EmailTestRequest, EmailTestResponse, PermissionRead, RoleListResponse, RoleRead, RoleUpdate
from app.services.audit_service import write_audit
from app.services.email import EmailDeliveryError, test_configured_email
from app.services.permission_service import CRITICAL_ADMIN_PERMISSIONS, PERMISSIONS, replace_role_permissions

router = APIRouter(prefix="/api/admin/settings", tags=["admin-settings"])


def serialize_email_settings(settings: EmailSettings | None) -> EmailSettingsRead:
    if not settings:
        return EmailSettingsRead()
    return EmailSettingsRead(
        provider=settings.provider,
        email_address=settings.email_address,
        from_name=settings.from_name,
        reply_to=settings.reply_to,
        enabled=settings.enabled,
        status=settings.status,
        has_app_password=bool(settings.encrypted_app_password),
        last_test_at=settings.last_test_at,
        last_test_result=settings.last_test_result,
        last_error=settings.last_error,
    )


def get_or_create_email_settings(db: Session) -> EmailSettings:
    settings = db.scalar(select(EmailSettings).order_by(EmailSettings.created_at.asc()).limit(1))
    if settings:
        return settings
    settings = EmailSettings()
    db.add(settings)
    db.flush()
    return settings


def serialize_role(db: Session, role: PortalRole) -> RoleRead:
    permission_keys = db.scalars(select(RolePermission.permission_key).where(RolePermission.role_id == role.id)).all()
    users_count = db.scalar(select(func.count()).select_from(User).where(User.role == role.key)) or 0
    return RoleRead(
        id=role.id,
        key=role.key,
        name=role.name,
        description=role.description,
        system=role.system,
        users_count=users_count,
        permission_keys=sorted(permission_keys),
    )


@router.get("/roles", response_model=RoleListResponse)
def list_roles(_: User = Depends(require_permission("roles.view")), db: Session = Depends(get_db)) -> RoleListResponse:
    roles = db.scalars(select(PortalRole).order_by(PortalRole.system.desc(), PortalRole.name)).all()
    permissions = [
        PermissionRead(key=item.key, label=item.label, group=item.group, description=item.description)
        for item in db.scalars(select(PortalPermission).order_by(PortalPermission.group, PortalPermission.key)).all()
    ]
    if not permissions:
        permissions = [PermissionRead(key=item.key, label=item.label, group=item.group, description=item.description) for item in PERMISSIONS]
    return RoleListResponse(
        roles=[serialize_role(db, role) for role in roles],
        permissions=permissions,
        critical_permissions=sorted(CRITICAL_ADMIN_PERMISSIONS),
    )


@router.put("/roles/{role_key}", response_model=RoleRead)
def update_role_permissions(
    role_key: str,
    payload: RoleUpdate,
    request: Request,
    admin_user: User = Depends(require_permission("roles.edit")),
    db: Session = Depends(get_db),
) -> RoleRead:
    role = db.scalar(select(PortalRole).where(PortalRole.key == role_key))
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
    permission_keys = set(payload.permission_keys)
    if role.key == "ADMINISTRATOR" and not CRITICAL_ADMIN_PERMISSIONS.issubset(permission_keys):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin must retain Settings, Roles, and Users administration access.")
    try:
        replace_role_permissions(db, role, permission_keys)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    write_audit(
        db,
        event_type="ROLE_PERMISSIONS_CHANGED",
        result="SUCCESS",
        user_id=admin_user.id,
        ip_address=request.client.host if request.client else None,
        target_type="ROLE",
        target_id=role.key,
        metadata={"permission_count": len(permission_keys)},
    )
    db.commit()
    return serialize_role(db, role)


@router.get("/email", response_model=EmailSettingsRead)
def get_email_settings(_: User = Depends(require_permission("email_settings.view")), db: Session = Depends(get_db)) -> EmailSettingsRead:
    settings = db.scalar(select(EmailSettings).order_by(EmailSettings.created_at.asc()).limit(1))
    return serialize_email_settings(settings)


@router.put("/email", response_model=EmailSettingsRead)
def update_email_settings(
    payload: EmailSettingsUpdate,
    request: Request,
    admin_user: User = Depends(require_permission("email_settings.edit")),
    db: Session = Depends(get_db),
) -> EmailSettingsRead:
    settings = get_or_create_email_settings(db)
    replacing_secret = payload.app_password is not None and payload.app_password.strip() != ""
    if not settings.encrypted_app_password and not replacing_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gmail App Password is required for initial configuration.")
    settings.provider = payload.provider
    settings.email_address = payload.email_address.lower()
    settings.from_name = payload.from_name.strip()
    settings.reply_to = payload.reply_to.lower() if payload.reply_to else None
    settings.enabled = payload.enabled
    settings.status = EmailStatus.CONFIGURED if payload.enabled else EmailStatus.CONFIGURED
    settings.last_error = None
    settings.updated_by = admin_user.id
    if replacing_secret:
        settings.encrypted_app_password = encrypt_secret(payload.app_password.strip())
    write_audit(
        db,
        event_type="EMAIL_CONFIGURATION_UPDATED",
        result="SUCCESS",
        user_id=admin_user.id,
        ip_address=request.client.host if request.client else None,
        target_type="EMAIL_SETTINGS",
        metadata={"provider": payload.provider.value, "enabled": payload.enabled, "secret_replaced": replacing_secret},
    )
    write_audit(
        db,
        event_type="EMAIL_ENABLED" if payload.enabled else "EMAIL_DISABLED",
        result="SUCCESS",
        user_id=admin_user.id,
        ip_address=request.client.host if request.client else None,
        target_type="EMAIL_SETTINGS",
    )
    db.commit()
    db.refresh(settings)
    return serialize_email_settings(settings)


@router.post("/email/test", response_model=EmailTestResponse)
def send_test_email(
    payload: EmailTestRequest,
    request: Request,
    admin_user: User = Depends(require_permission("email_settings.test")),
    db: Session = Depends(get_db),
) -> EmailTestResponse:
    settings = get_or_create_email_settings(db)
    try:
        test_configured_email(db, str(payload.recipient))
    except EmailDeliveryError as exc:
        settings.status = EmailStatus.ERROR
        settings.last_test_at = utcnow()
        settings.last_test_result = "FAILURE"
        settings.last_error = exc.public_message
        write_audit(db, event_type="TEST_EMAIL_REQUESTED", result="FAILURE", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="EMAIL_SETTINGS", metadata={"recipient": str(payload.recipient)})
        db.commit()
        return EmailTestResponse(status=EmailStatus.ERROR, message=exc.public_message)
    settings.status = EmailStatus.VERIFIED
    settings.last_test_at = utcnow()
    settings.last_test_result = "SUCCESS"
    settings.last_error = None
    write_audit(db, event_type="TEST_EMAIL_REQUESTED", result="SUCCESS", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="EMAIL_SETTINGS", metadata={"recipient": str(payload.recipient)})
    db.commit()
    return EmailTestResponse(status=EmailStatus.VERIFIED, message="Test email sent successfully.")
