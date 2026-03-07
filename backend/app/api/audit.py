"""
Audit API — Audit trail and immutable log query endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_trail import AuditTrail
from app.models.immutable_log import ImmutableLog
from app.schemas.audit import AuditTimelineEntry, AuditTimelineResponse
from app.schemas.sar import AuditTrailResponse
from app.services.audit_service import get_case_timeline, verify_case_chain

router = APIRouter()


@router.get("/{case_id}", response_model=list[AuditTrailResponse])
async def get_audit_trail(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all structured audit trail records for a case.
    Supervisor+ access required — contains full reasoning trace.
    """
    result = await db.execute(
        select(AuditTrail)
        .where(AuditTrail.case_id == case_id)
        .order_by(AuditTrail.timestamp.desc())
    )
    trails = result.scalars().all()

    if not trails:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No audit trails found for this case",
        )

    return [AuditTrailResponse.model_validate(t) for t in trails]


@router.get("/{case_id}/timeline", response_model=AuditTimelineResponse)
async def get_audit_timeline(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the immutable log timeline for a case with hash chain verification.
    
    Returns all log entries chronologically along with a boolean
    indicating whether the hash chain integrity is intact.
    """
    entries = await get_case_timeline(db, case_id)
    chain_valid = await verify_case_chain(db, case_id)

    return AuditTimelineResponse(
        case_id=case_id,
        entries=[AuditTimelineEntry.model_validate(e) for e in entries],
        chain_valid=chain_valid,
    )
