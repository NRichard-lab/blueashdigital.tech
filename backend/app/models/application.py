import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ApplicationType(str, enum.Enum):
    INTERNAL_WEB = "INTERNAL_WEB"
    INTERNAL_SERVICE = "INTERNAL_SERVICE"
    EXTERNAL_URL = "EXTERNAL_URL"
    API_APP = "API_APP"


class ApplicationStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"
    MAINTENANCE = "MAINTENANCE"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    icon: Mapped[str] = mapped_column(String(64), nullable=False, default="APP")
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="Utilities", index=True)
    application_type: Mapped[ApplicationType] = mapped_column(Enum(ApplicationType, name="app_type_enum"), nullable=False)
    launch_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    internal_service_url: Mapped[str | None] = mapped_column(String(2048))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    administrator_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    health_check_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus, name="app_status_enum"), nullable=False, default=ApplicationStatus.UNKNOWN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    users = relationship("UserApplication", back_populates="application", cascade="all, delete-orphan")


class UserApplication(Base):
    __tablename__ = "user_applications"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="applications")
    application = relationship("Application", back_populates="users")

