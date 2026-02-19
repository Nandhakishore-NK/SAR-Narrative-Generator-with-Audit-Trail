"""
Case Model — Central entity linking alerts, transactions, and SAR narratives.

Status lifecycle:
  open → under_review → sar_generated → escalated → closed
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Enum as SAEnum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class CaseStatus(str, enum.Enum):
    open = "open"
    under_review = "under_review"
    sar_generated = "sar_generated"
    escalated = "escalated"
    closed = "closed"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    # Customer identification
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_type: Mapped[str] = mapped_column(String(50), nullable=True)  # individual / entity
    customer_risk_rating: Mapped[str] = mapped_column(String(20), nullable=True)

    # KYC information stored as structured text
    kyc_id_type: Mapped[str] = mapped_column(String(50), nullable=True)
    kyc_id_number: Mapped[str] = mapped_column(String(100), nullable=True)
    kyc_country: Mapped[str] = mapped_column(String(100), nullable=True)
    kyc_occupation: Mapped[str] = mapped_column(String(255), nullable=True)
    kyc_onboarding_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Account summary
    account_number: Mapped[str] = mapped_column(String(50), nullable=True)
    account_type: Mapped[str] = mapped_column(String(50), nullable=True)
    account_open_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    account_balance: Mapped[float] = mapped_column(nullable=True)
    account_currency: Mapped[str] = mapped_column(String(10), nullable=True, default="USD")

    # Alert metadata
    alert_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    alert_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(100), nullable=True)
    alert_score: Mapped[float] = mapped_column(nullable=True)

    # Case status
    status: Mapped[CaseStatus] = mapped_column(
        SAEnum(CaseStatus, name="case_status_enum"),
        nullable=False,
        default=CaseStatus.open,
    )

    # Case notes (analyst-entered context)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Historical behavior summary
    historical_avg_monthly_volume: Mapped[float] = mapped_column(nullable=True)
    historical_avg_transaction_size: Mapped[float] = mapped_column(nullable=True)
    historical_counterparty_count: Mapped[int] = mapped_column(nullable=True)
    historical_sar_count: Mapped[int] = mapped_column(nullable=True, default=0)

    # Risk scores
    composite_risk_score: Mapped[float] = mapped_column(nullable=True)
    network_risk_score: Mapped[float] = mapped_column(nullable=True)
    behavioral_risk_score: Mapped[float] = mapped_column(nullable=True)

    # Graph relationship analysis (stored as text summary)
    graph_analysis: Mapped[str] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    transactions = relationship("Transaction", back_populates="case", cascade="all, delete-orphan")
    rule_triggers = relationship("RuleTrigger", back_populates="case", cascade="all, delete-orphan")
    narratives = relationship("SarNarrative", back_populates="case", cascade="all, delete-orphan")
    audit_trails = relationship("AuditTrail", back_populates="case", cascade="all, delete-orphan")
