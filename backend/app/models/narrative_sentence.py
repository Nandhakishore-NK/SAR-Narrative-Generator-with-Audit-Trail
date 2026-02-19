"""
Narrative Sentence Model — Individual sentences from a SAR narrative.

Each sentence is:
- SHA256 hashed for tamper detection
- Assigned a confidence level (LOW, MEDIUM, HIGH)
- Linked to supporting evidence via the audit trail reasoning_trace
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class ConfidenceLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class NarrativeSentence(Base):
    __tablename__ = "narrative_sentences"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    narrative_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sar_narratives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sentence_index: Mapped[int] = mapped_column(nullable=False)
    sentence_text: Mapped[str] = mapped_column(Text, nullable=False)
    sentence_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 hex digest

    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        SAEnum(ConfidenceLevel, name="confidence_level_enum"),
        nullable=False,
        default=ConfidenceLevel.MEDIUM,
    )

    # Evidence linkage fields (populated from audit JSON)
    supporting_transaction_ids: Mapped[str] = mapped_column(Text, nullable=True)  # comma-separated UUIDs
    rule_reference: Mapped[str] = mapped_column(String(100), nullable=True)
    threshold_reference: Mapped[str] = mapped_column(String(255), nullable=True)
    typology_reference: Mapped[str] = mapped_column(String(255), nullable=True)
    graph_reference: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    narrative = relationship("SarNarrative", back_populates="sentences")
    overrides = relationship("Override", back_populates="sentence", cascade="all, delete-orphan")
