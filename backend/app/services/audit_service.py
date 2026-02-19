"""
Audit Service — Immutable log writer with hash-chain integrity.

Every significant system action is recorded as an append-only log entry.
Each entry's hash incorporates the previous entry's hash, forming a
tamper-evident chain that can be verified at any time.

Actions logged:
- case_created, case_updated
- narrative_generated
- override_submitted, override_approved, override_rejected
- sentence_modified
"""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.immutable_log import ImmutableLog
from app.services.hash_service import hash_log_entry, verify_hash_chain


async def write_immutable_log(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    action: str,
    actor_id: Optional[str] = None,
    details: Optional[str] = None,
) -> ImmutableLog:
    """
    Append a new entry to the immutable log.
    Automatically chains to the previous entry's hash.
    
    This function enforces append-only behavior:
    - No updates to existing entries
    - No deletes
    - Each new entry references the previous hash
    """
    # Get the most recent log entry to chain from
    result = await db.execute(
        select(ImmutableLog).order_by(desc(ImmutableLog.timestamp)).limit(1)
    )
    last_entry = result.scalar_one_or_none()
    previous_hash = last_entry.hash_signature if last_entry else None

    now = datetime.now(timezone.utc)
    
    # Generate hash incorporating previous entry (chain integrity)
    hash_sig = hash_log_entry(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        timestamp=now.isoformat(),
        previous_hash=previous_hash,
    )

    log_entry = ImmutableLog(
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        actor_id=str(actor_id) if actor_id else None,
        details=details,
        previous_hash=previous_hash,
        hash_signature=hash_sig,
        timestamp=now,
    )

    db.add(log_entry)
    await db.flush()  # Ensure ID is assigned but don't commit (caller controls transaction)
    return log_entry


async def get_case_timeline(db: AsyncSession, case_id: UUID) -> list:
    """
    Get all immutable log entries related to a case.
    Returns entries ordered chronologically.
    """
    case_id_str = str(case_id)
    result = await db.execute(
        select(ImmutableLog)
        .where(ImmutableLog.entity_id == case_id_str)
        .order_by(ImmutableLog.timestamp.asc())
    )
    return list(result.scalars().all())


async def verify_case_chain(db: AsyncSession, case_id: UUID) -> bool:
    """
    Verify the hash chain integrity for all logs related to a case.
    Returns True if chain is valid, False if tampering detected.
    """
    entries = await get_case_timeline(db, case_id)
    if not entries:
        return True
    return verify_hash_chain(entries)
