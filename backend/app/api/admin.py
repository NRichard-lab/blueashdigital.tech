import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.security import hash_password
from app.database.session import get_db
from app.models.application import Application, UserApplication
from app.models.audit import AuditLog
from app.models.mfa import MfaMethod
from app.models.password_reset import PasswordResetToken
from app.models.session import PortalSession
from app.models.user import Role, User
from app.schemas.application import ApplicationRead
from app.schemas.user import PasswordResetRequest, UserCreate, UserListResponse, UserRead, UserUpdate
from app.services.auth_service import revoke_user_auth_state
from app.services.application_auth_service import revoke_application_auth_for_user
from app.services.audit_service import write_audit
from app.services.mfa_email_service import invalidate_user_mfa_state

router = APIRouter(prefix="/api/admin", tags=["admin"])


def serialize_user(db: Session, user: User) -> UserRead:
    application_ids = db.scalars(select(UserApplication.application_id).where(UserApplication.user_id == user.id)).all()
    mfa_enabled = db.scalar(select(func.count()).select_from(MfaMethod).where(MfaMethod.user_id == user.id, MfaMethod.enabled.is_(True))) > 0
    payload = UserRead.model_validate(user)
    payload.application_ids = list(application_ids)
    payload.applications_assigned = len(application_ids)
    payload.mfa_enabled = bool(mfa_enabled)
    payload.mfa_required = user.role == Role.ADMINISTRATOR or user.mfa_required
    return payload


def ensure_admin_remains(db: Session, target: User, *, new_role: Role | None = None, enabled: bool | None = None, deleting: bool = False) -> None:
    removes_admin = target.role == Role.ADMINISTRATOR and (
        deleting or new_role == Role.USER or enabled is False
    )
    if not removes_admin:
        return
    admin_count = db.scalar(select(func.count()).select_from(User).where(User.role == Role.ADMINISTRATOR, User.enabled.is_(True)))
    if admin_count <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one enabled administrator account must remain.")


def replace_assignments(db: Session, user: User, application_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    previous_ids = set(db.scalars(select(UserApplication.application_id).where(UserApplication.user_id == user.id)).all())
    db.execute(delete(UserApplication).where(UserApplication.user_id == user.id))
    if not application_ids:
        return previous_ids
    valid_ids = set(db.scalars(select(Application.id).where(Application.id.in_(application_ids))).all())
    missing = set(application_ids) - valid_ids
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more selected applications do not exist.")
    for application_id in sorted(valid_ids, key=str):
        db.add(UserApplication(user_id=user.id, application_id=application_id))
    return previous_ids - valid_ids


def revoke_user_sessions(db: Session, user_id: uuid.UUID) -> None:
    revoke_user_auth_state(db, user_id)


@router.get("/users", response_model=UserListResponse)
def list_users(
    _: User = Depends(require_permission("users.view")),
    db: Session = Depends(get_db),
    search: str = "",
    role: Role | None = None,
    enabled: bool | None = None,
    limit: int = 25,
    offset: int = 0,
) -> UserListResponse:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    statement = select(User)
    count_statement = select(func.count()).select_from(User)
    filters = []
    if search.strip():
        pattern = f"%{search.strip().lower()}%"
        filters.append(or_(func.lower(User.username).like(pattern), func.lower(User.email).like(pattern), func.lower(User.display_name).like(pattern)))
    if role:
        filters.append(User.role == role)
    if enabled is not None:
        filters.append(User.enabled.is_(enabled))
    for item in filters:
        statement = statement.where(item)
        count_statement = count_statement.where(item)
    users = db.scalars(statement.order_by(User.created_at.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(count_statement) or 0
    return UserListResponse(items=[serialize_user(db, user) for user in users], total=total, limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(user_id: uuid.UUID, _: User = Depends(require_permission("users.view")), db: Session = Depends(get_db)) -> UserRead:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return serialize_user(db, user)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, request: Request, admin_user: User = Depends(require_permission("users.create")), db: Session = Depends(get_db)) -> UserRead:
    existing = db.scalar(select(User).where(or_(User.username == payload.username, User.email == payload.email.lower())))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email is already in use.")
    user = User(
        username=payload.username,
        email=payload.email.lower(),
        display_name=payload.display_name,
        password_hash=hash_password(payload.temporary_password),
        role=payload.role,
        enabled=payload.enabled,
        mfa_required=True if payload.role == Role.ADMINISTRATOR else payload.mfa_required,
    )
    db.add(user)
    db.flush()
    replace_assignments(db, user, payload.application_ids)
    write_audit(db, event_type="USER_CREATED", result="SUCCESS", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="USER", target_id=str(user.id), metadata={"username": user.username, "role": user.role.value})
    db.commit()
    db.refresh(user)
    return serialize_user(db, user)


@router.put("/users/{user_id}", response_model=UserRead)
def update_user(user_id: uuid.UUID, payload: UserUpdate, request: Request, admin_user: User = Depends(require_permission("users.edit")), db: Session = Depends(get_db)) -> UserRead:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    duplicate = db.scalar(select(User).where(User.email == payload.email.lower(), User.id != user.id))
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already in use.")
    if user.id == admin_user.id and (payload.enabled is False or payload.role != Role.ADMINISTRATOR):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot disable or demote your own active administrator account.")
    ensure_admin_remains(db, user, new_role=payload.role, enabled=payload.enabled)
    previous_role = user.role
    previous_enabled = user.enabled
    previous_mfa_required = user.mfa_required
    user.email = payload.email.lower()
    user.display_name = payload.display_name
    user.role = payload.role
    user.enabled = payload.enabled
    user.mfa_required = True if payload.role == Role.ADMINISTRATOR else payload.mfa_required
    removed_application_ids = replace_assignments(db, user, payload.application_ids)
    security_policy_changed = previous_role != user.role or previous_mfa_required != user.mfa_required
    if (previous_enabled and not user.enabled) or security_policy_changed:
        revoke_user_sessions(db, user.id)
    elif removed_application_ids:
        revoke_application_auth_for_user(
            db,
            user.id,
            reason="APPLICATION_ASSIGNMENT_REMOVED",
            application_ids=removed_application_ids,
        )
    if previous_enabled and not user.enabled:
        write_audit(db, event_type="USER_DISABLED", result="SUCCESS", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="USER", target_id=str(user.id))
    elif not previous_enabled and user.enabled:
        write_audit(db, event_type="USER_ENABLED", result="SUCCESS", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="USER", target_id=str(user.id))
    if previous_role != user.role:
        write_audit(db, event_type="USER_ROLE_CHANGED", result="SUCCESS", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="USER", target_id=str(user.id), metadata={"from": previous_role.value, "to": user.role.value})
    write_audit(db, event_type="USER_EDITED", result="SUCCESS", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="USER", target_id=str(user.id))
    write_audit(db, event_type="USER_APPLICATIONS_CHANGED", result="SUCCESS", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="USER", target_id=str(user.id), metadata={"application_count": len(payload.application_ids)})
    db.commit()
    db.refresh(user)
    return serialize_user(db, user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, request: Request, admin_user: User = Depends(require_permission("users.delete")), db: Session = Depends(get_db)) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.id == admin_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own active administrator account.")
    ensure_admin_remains(db, user, deleting=True)
    db.execute(delete(UserApplication).where(UserApplication.user_id == user.id))
    db.execute(delete(PortalSession).where(PortalSession.user_id == user.id))
    db.execute(delete(MfaMethod).where(MfaMethod.user_id == user.id))
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    invalidate_user_mfa_state(db, user.id)
    write_audit(db, event_type="USER_DELETED", result="SUCCESS", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="USER", target_id=str(user.id), metadata={"username": user.username})
    db.delete(user)
    db.commit()


@router.post("/users/{user_id}/reset-password", response_model=UserRead)
def reset_password(user_id: uuid.UUID, payload: PasswordResetRequest, request: Request, admin_user: User = Depends(require_permission("users.edit")), db: Session = Depends(get_db)) -> UserRead:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.password_hash = hash_password(payload.temporary_password)
    user.force_password_change = payload.force_password_change
    revoke_user_sessions(db, user.id)
    write_audit(db, event_type="USER_PASSWORD_RESET", result="SUCCESS", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="USER", target_id=str(user.id))
    db.commit()
    db.refresh(user)
    return serialize_user(db, user)


@router.post("/users/{user_id}/reset-mfa", response_model=UserRead)
def reset_mfa(user_id: uuid.UUID, request: Request, admin_user: User = Depends(require_permission("users.edit")), db: Session = Depends(get_db)) -> UserRead:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    db.execute(delete(MfaMethod).where(MfaMethod.user_id == user.id))
    revoke_user_sessions(db, user.id)
    write_audit(db, event_type="USER_MFA_RESET", result="SUCCESS", user_id=admin_user.id, ip_address=request.client.host if request.client else None, target_type="USER", target_id=str(user.id))
    db.commit()
    db.refresh(user)
    return serialize_user(db, user)


@router.get("/applications", response_model=list[ApplicationRead])
def list_admin_applications(_: User = Depends(require_permission("applications_admin.view")), db: Session = Depends(get_db)) -> list[ApplicationRead]:
    apps = db.scalars(select(Application).order_by(Application.display_order, Application.name)).all()
    return [ApplicationRead.model_validate(app) for app in apps]


@router.get("/audit")
def list_audit(_: User = Depends(require_permission("audit.view")), db: Session = Depends(get_db), limit: int = 25, offset: int = 0):
    limit = max(1, min(limit, 100))
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)).all()
    return [
        {
            "id": str(log.id),
            "event_type": log.event_type,
            "result": log.result,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "created_at": log.created_at,
        }
        for log in logs
    ]
