from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.database.session import get_db
from app.models.application import Application, UserApplication
from app.models.user import Role, User
from app.schemas.application import ApplicationRead

router = APIRouter(prefix="/api/apps", tags=["applications"])


@router.get("", response_model=list[ApplicationRead])
def list_applications(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[ApplicationRead]:
    statement = select(Application).where(Application.enabled.is_(True)).order_by(Application.display_order, Application.name)
    if user.role != Role.ADMINISTRATOR:
        statement = statement.join(UserApplication).where(UserApplication.user_id == user.id, Application.administrator_only.is_(False))
    apps = db.scalars(statement).all()
    return [ApplicationRead.model_validate(app) for app in apps]

