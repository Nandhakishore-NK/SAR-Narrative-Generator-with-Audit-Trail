"""
Overrides API — Evidence-backed manual override endpoints.

Governance enforcement:
1. Submit override → requires reason code + evidence reference
2. If HIGH/CRITICAL severity → requires supervisor approval
3. Approve/reject override → supervisor/admin only, cannot self-approve
4. All actions logged immutably
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.override import Override
from app.models.user import User
from app.schemas.override import OverrideCreate, OverrideApproval, OverrideResponse
from app.middleware.role_guard import require_analyst, require_supervisor
from app.services.override_service import validate_and_create_override, approve_override

router = APIRouter()


@router.post("/", response_model=OverrideResponse, status_code=status.HTTP_201_CREATED)
async def submit_override(
    payload: OverrideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Submit a manual override for a narrative sentence.
    
    Governance enforced:
    - Valid reason code required
    - Evidence reference required (minimum 10 characters)
    - Original hash must match current sentence hash
    - LOW/MEDIUM severity: auto-approved
    - HIGH/CRITICAL severity: pending supervisor approval
    """
    override = await validate_and_create_override(
        db=db,
        sentence_id=payload.sentence_id,
        modified_text=payload.modified_text,
        reason_code=payload.override_reason_code,
        evidence_reference=payload.evidence_reference,
        analyst=current_user,
    )
    return OverrideResponse.model_validate(override)


@router.patch("/{override_id}/approve", response_model=OverrideResponse)
async def approve_or_reject_override(
    override_id: UUID,
    payload: OverrideApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_supervisor),
):
    """
    Approve or reject a pending override.
    
    Governance enforced:
    - Only supervisors and admins can approve
    - Analyst cannot approve their own override
    - Override must be in pending status
    - Approval notes logged in audit trail
    """
    override = await approve_override(
        db=db,
        override_id=override_id,
        supervisor=current_user,
        approval_status=payload.approval_status,
        approval_notes=payload.approval_notes,
    )
    return OverrideResponse.model_validate(override)


@router.get("/sentence/{sentence_id}", response_model=List[OverrideResponse])
async def get_sentence_overrides(
    sentence_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """Get all overrides for a specific sentence."""
    result = await db.execute(
        select(Override)
        .where(Override.sentence_id == sentence_id)
        .order_by(Override.created_at.desc())
    )
    overrides = result.scalars().all()
    return [OverrideResponse.model_validate(o) for o in overrides]


@router.get("/pending", response_model=List[OverrideResponse])
async def get_pending_overrides(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_supervisor),
):
    """Get all pending overrides awaiting supervisor approval."""
    result = await db.execute(
        select(Override)
        .where(Override.approval_status == "pending")
        .order_by(Override.created_at.asc())
    )
    overrides = result.scalars().all()
    return [OverrideResponse.model_validate(o) for o in overrides]
