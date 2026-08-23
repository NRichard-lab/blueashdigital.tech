import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.database.session import get_db
from app.models.application import Application, UserApplication
from app.models.user import Role, User
from app.schemas.application import ApplicationRead

router = APIRouter(prefix="/api/apps", tags=["applications"])


@router.get("", response_model=list[ApplicationRead])
def list_applications(user: User = Depends(require_permission("applications.view")), db: Session = Depends(get_db)) -> list[ApplicationRead]:
    statement = select(Application).where(Application.enabled.is_(True)).order_by(Application.display_order, Application.name)
    if user.role != Role.ADMINISTRATOR:
        statement = statement.join(UserApplication).where(UserApplication.user_id == user.id, Application.administrator_only.is_(False))
    apps = db.scalars(statement).all()
    return [ApplicationRead.model_validate(app) for app in apps]


@router.get("/{application_id}/launch")
def launch_application(application_id: uuid.UUID, user: User = Depends(require_permission("applications.launch")), db: Session = Depends(get_db)) -> dict[str, str]:
    statement = select(Application).where(Application.id == application_id, Application.enabled.is_(True))
    if user.role != Role.ADMINISTRATOR:
        statement = statement.join(UserApplication).where(UserApplication.user_id == user.id, Application.administrator_only.is_(False))
    app = db.scalar(statement)
    if not app:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this application.")
    return {"launch_url": app.launch_url}
