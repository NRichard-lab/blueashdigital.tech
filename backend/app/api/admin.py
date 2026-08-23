from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import administrator
from app.database.session import get_db
from app.models.application import Application
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.application import ApplicationRead
from app.schemas.user import UserRead

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserRead])
def list_users(_: User = Depends(administrator), db: Session = Depends(get_db)) -> list[UserRead]:
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return [UserRead.model_validate(user) for user in users]


@router.get("/applications", response_model=list[ApplicationRead])
def list_admin_applications(_: User = Depends(administrator), db: Session = Depends(get_db)) -> list[ApplicationRead]:
    apps = db.scalars(select(Application).order_by(Application.display_order, Application.name)).all()
    return [ApplicationRead.model_validate(app) for app in apps]


@router.get("/audit")
def list_audit(_: User = Depends(administrator), db: Session = Depends(get_db), limit: int = 25, offset: int = 0):
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

