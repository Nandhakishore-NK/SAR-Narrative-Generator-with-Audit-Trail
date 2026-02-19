"""
Immutable Log Model — Append-only audit log with hash-chain integrity.

Every significant system action (create, update, override, approval) is
recorded here. Each record links to the previous via hash_signature,
creating a tamper-evident chain.

This table enforces:
- Append-only writes (no updates or deletes at application level)
- Hash chain linking to detect tampering
- Full traceability of all system mutations
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImmutableLog(Base):
    __tablename__ = "immutable_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # created, updated, overridden, approved, rejected
    actor_id: Mapped[str] = mapped_column(String(100), nullable=True)  # user who performed action
    details: Mapped[str] = mapped_column(Text, nullable=True)

    # Hash chain: SHA256(previous_hash + entity_type + entity_id + action + timestamp)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    hash_signature: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
