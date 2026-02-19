"""
User Model — Role-based access control entity.

Roles:
  - analyst: Can create cases, generate SARs, submit overrides
  - supervisor: Can approve overrides, view audit trails
  - admin: Full system access
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Enum as SAEnum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    analyst = "analyst"
    supervisor = "supervisor"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role_enum"), nullable=False, default=UserRole.analyst
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    narratives = relationship("SarNarrative", back_populates="created_by_user")
    overrides_submitted = relationship(
        "Override", back_populates="analyst", foreign_keys="Override.analyst_id"
    )
    overrides_approved = relationship(
        "Override", back_populates="supervisor", foreign_keys="Override.supervisor_id"
    )
