from fastapi import APIRouter, Depends

from app.api.dependencies import current_user
from app.models.user import User
from app.schemas.user import CurrentUser, current_user_payload

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me", response_model=CurrentUser)
def me(user: User = Depends(current_user)) -> CurrentUser:
    return current_user_payload(user)
