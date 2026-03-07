"""
SAR Generation API — Endpoint for generating SAR narratives.
"""

from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.case import Case
from app.models.sar_narrative import SarNarrative
from app.models.narrative_sentence import NarrativeSentence
from app.schemas.sar import SarGenerateRequest, SarNarrativeResponse, SentenceBreakdown, AuditTrailResponse
from app.models.audit_trail import AuditTrail
from app.services.sar_engine import generate_sar

router = APIRouter()

SYSTEM_ACTOR = "system"


@router.post("/generate", response_model=SarNarrativeResponse)
async def generate_sar_narrative(
    request: SarGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a SAR narrative for a case.
    
    This endpoint:
    - Validates the case exists and has transaction data
    - Calls the SAR generation engine
    - Returns the narrative with sentence breakdowns
    - Creates a complete audit trail record
    """
    # Validate case exists
    result = await db.execute(select(Case).where(Case.id == request.case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    try:
        narrative, audit_trail = await generate_sar(
            db=db,
            case_id=request.case_id,
            user_id=SYSTEM_ACTOR,
            analyst_role="analyst",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SAR generation failed: {str(e)}",
        )

    # Load sentences for response
    sent_result = await db.execute(
        select(NarrativeSentence)
        .where(NarrativeSentence.narrative_id == narrative.id)
        .order_by(NarrativeSentence.sentence_index.asc())
    )
    sentences = sent_result.scalars().all()

    sentence_breakdowns = [
        SentenceBreakdown(
            sentence_id=s.id,
            sentence_index=s.sentence_index,
            sentence_text=s.sentence_text,
            sentence_hash=s.sentence_hash,
            confidence_level=s.confidence_level.value,
            supporting_transaction_ids=s.supporting_transaction_ids.split(",") if s.supporting_transaction_ids else [],
            rule_reference=s.rule_reference,
            threshold_reference=s.threshold_reference,
            typology_reference=s.typology_reference,
            graph_reference=s.graph_reference,
        )
        for s in sentences
    ]

    return SarNarrativeResponse(
        narrative_id=narrative.id,
        case_id=narrative.case_id,
        narrative_text=narrative.narrative_text,
        version=narrative.version,
        severity=narrative.severity,
        is_active=narrative.is_active,
        created_by=narrative.created_by,
        created_at=narrative.created_at,
        sentences=sentence_breakdowns,
    )


@router.get("/cases/{case_id}/narrative", response_model=Optional[SarNarrativeResponse])
async def get_active_narrative(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the currently active SAR narrative for a case."""
    result = await db.execute(
        select(SarNarrative).where(
            SarNarrative.case_id == case_id,
            SarNarrative.is_active == True,
        )
    )
    narrative = result.scalar_one_or_none()

    if not narrative:
        return None

    # Load sentences
    sent_result = await db.execute(
        select(NarrativeSentence)
        .where(NarrativeSentence.narrative_id == narrative.id)
        .order_by(NarrativeSentence.sentence_index.asc())
    )
    sentences = sent_result.scalars().all()

    sentence_breakdowns = [
        SentenceBreakdown(
            sentence_id=s.id,
            sentence_index=s.sentence_index,
            sentence_text=s.sentence_text,
            sentence_hash=s.sentence_hash,
            confidence_level=s.confidence_level.value,
            supporting_transaction_ids=s.supporting_transaction_ids.split(",") if s.supporting_transaction_ids else [],
            rule_reference=s.rule_reference,
            threshold_reference=s.threshold_reference,
            typology_reference=s.typology_reference,
            graph_reference=s.graph_reference,
        )
        for s in sentences
    ]

    return SarNarrativeResponse(
        narrative_id=narrative.id,
        case_id=narrative.case_id,
        narrative_text=narrative.narrative_text,
        version=narrative.version,
        severity=narrative.severity,
        is_active=narrative.is_active,
        created_by=narrative.created_by,
        created_at=narrative.created_at,
        sentences=sentence_breakdowns,
    )


@router.get("/cases/{case_id}/audit", response_model=List[AuditTrailResponse])
async def get_case_audit_trails(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all audit trail records for a case."""
    result = await db.execute(
        select(AuditTrail)
        .where(AuditTrail.case_id == case_id)
        .order_by(AuditTrail.timestamp.desc())
    )
    trails = result.scalars().all()
    return [AuditTrailResponse.model_validate(t) for t in trails]
