"""
Transaction Model — Individual financial transactions linked to a case.

Each transaction record serves as primary evidence for SAR narrative claims.
Transaction IDs are referenced in the audit trail reasoning_trace.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Transaction details
    transaction_ref: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=True)  # wire, cash, ach, etc.
    direction: Mapped[str] = mapped_column(String(10), nullable=True)  # inbound / outbound

    # Counterparty information
    counterparty_name: Mapped[str] = mapped_column(String(255), nullable=True)
    counterparty_account: Mapped[str] = mapped_column(String(100), nullable=True)
    counterparty_bank: Mapped[str] = mapped_column(String(255), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=True)

    # Additional metadata
    purpose: Mapped[str] = mapped_column(Text, nullable=True)
    is_flagged: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    case = relationship("Case", back_populates="transactions")
