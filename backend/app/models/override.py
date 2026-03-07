"""
Override Model — Evidence-backed manual edits to narrative sentences.

Governance rules enforced:
1. ALL overrides require: reason code + evidence reference + sentence hash comparison
2. HIGH/CRITICAL severity: supervisor approval mandatory
3. Analyst cannot approve own override
4. All changes logged immutably
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class OverrideReasonCode(str, enum.Enum):
    factual_correction = "factual_correction"
    additional_evidence = "additional_evidence"
    regulatory_update = "regulatory_update"
    typology_reclassification = "typology_reclassification"
    risk_reassessment = "risk_reassessment"
    data_quality_issue = "data_quality_issue"
    supervisor_directed = "supervisor_directed"


class Override(Base):
    __tablename__ = "overrides"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    sentence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("narrative_sentences.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Hash comparison for tamper detection
    original_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    modified_text: Mapped[str] = mapped_column(Text, nullable=False)
    modified_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Governance fields — all mandatory
    override_reason_code: Mapped[OverrideReasonCode] = mapped_column(
        SAEnum(OverrideReasonCode, name="override_reason_code_enum"), nullable=False
    )
    evidence_reference: Mapped[str] = mapped_column(Text, nullable=False)

    # Role enforcement
    analyst_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    supervisor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(ApprovalStatus, name="approval_status_enum"),
        nullable=False,
        default=ApprovalStatus.pending,
    )
    approval_notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    sentence = relationship("NarrativeSentence", back_populates="overrides")
    analyst = relationship("User", back_populates="overrides_submitted", foreign_keys=[analyst_id])
    supervisor = relationship("User", back_populates="overrides_approved", foreign_keys=[supervisor_id])
