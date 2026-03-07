"""
Overrides API — Evidence-backed manual override endpoints.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.override import Override
from app.schemas.override import OverrideCreate, OverrideApproval, OverrideResponse
from app.services.override_service import validate_and_create_override, approve_override

router = APIRouter()

SYSTEM_ACTOR = "system"


@router.post("/", response_model=OverrideResponse, status_code=status.HTTP_201_CREATED)
async def submit_override(
    payload: OverrideCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a manual override for a narrative sentence.
    """
    override = await validate_and_create_override(
        db=db,
        sentence_id=payload.sentence_id,
        modified_text=payload.modified_text,
        reason_code=payload.override_reason_code,
        evidence_reference=payload.evidence_reference,
        analyst_id=SYSTEM_ACTOR,
    )
    return OverrideResponse.model_validate(override)


@router.patch("/{override_id}/approve", response_model=OverrideResponse)
async def approve_or_reject_override(
    override_id: UUID,
    payload: OverrideApproval,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve or reject a pending override.
    """
    override = await approve_override(
        db=db,
        override_id=override_id,
        supervisor_id=SYSTEM_ACTOR,
        approval_status=payload.approval_status,
        approval_notes=payload.approval_notes,
    )
    return OverrideResponse.model_validate(override)


@router.get("/sentence/{sentence_id}", response_model=List[OverrideResponse])
async def get_sentence_overrides(
    sentence_id: UUID,
    db: AsyncSession = Depends(get_db),
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
):
    """Get all pending overrides awaiting supervisor approval."""
    result = await db.execute(
        select(Override)
        .where(Override.approval_status == "pending")
        .order_by(Override.created_at.asc())
    )
    overrides = result.scalars().all()
    return [OverrideResponse.model_validate(o) for o in overrides]
