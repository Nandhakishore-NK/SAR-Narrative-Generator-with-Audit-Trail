"""
Audit Trail Model — Complete structured audit record for each SAR generation.

Stores the full machine-parseable JSON audit trail including:
- Data sources used
- Triggering rules and thresholds breached
- Typology matches
- Graph anomalies
- Transaction IDs referenced
- Sentence-level reasoning trace
- Alert metadata and severity
- Data completeness metrics
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditTrail(Base):
    __tablename__ = "audit_trails"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Full structured audit JSON (Section B output)
    audit_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    narrative_version: Mapped[int] = mapped_column(nullable=False, default=1)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    case = relationship("Case", back_populates="audit_trails")
