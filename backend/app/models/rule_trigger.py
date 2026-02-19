"""
Rule Trigger Model — AML detection rules that fired for a case.

Each trigger records the rule code, threshold, and whether it was breached.
These map directly to the SAR narrative's typology section.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RuleTrigger(Base):
    __tablename__ = "rule_triggers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_description: Mapped[str] = mapped_column(Text, nullable=True)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=True)
    actual_value: Mapped[float] = mapped_column(Float, nullable=True)
    breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Typology mapping
    typology_code: Mapped[str] = mapped_column(String(50), nullable=True)
    typology_description: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    case = relationship("Case", back_populates="rule_triggers")
