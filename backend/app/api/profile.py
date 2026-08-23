from fastapi import APIRouter, Depends

from app.api.dependencies import current_user
from app.models.user import User
from app.schemas.user import CurrentUser

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me", response_model=CurrentUser)
def me(user: User = Depends(current_user)) -> CurrentUser:
    return CurrentUser.model_validate(user)

