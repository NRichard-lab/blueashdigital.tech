import uuid
from pydantic import BaseModel, HttpUrl

from app.models.application import ApplicationStatus, ApplicationType


class ApplicationRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str
    icon: str
    category: str
    application_type: ApplicationType
    launch_url: str
    enabled: bool
    administrator_only: bool
    status: ApplicationStatus

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    name: str
    slug: str
    description: str = ""
    icon: str = "APP"
    category: str = "Utilities"
    application_type: ApplicationType
    launch_url: HttpUrl
    administrator_only: bool = False

