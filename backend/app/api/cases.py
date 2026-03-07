"""
Cases API — Case CRUD with case-level data isolation.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.case import Case, CaseStatus
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse, CaseListResponse
from app.services.audit_service import write_immutable_log
from app.utils.helpers import sanitize_input

router = APIRouter()

SYSTEM_ACTOR = "system"


@router.get("/", response_model=List[CaseListResponse])
async def list_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List all cases with pagination and optional status filter.
    """
    query = select(Case).order_by(Case.created_at.desc()).offset(skip).limit(limit)

    if status_filter:
        try:
            case_status = CaseStatus(status_filter)
            query = query.where(Case.status == case_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter: {status_filter}",
            )

    result = await db.execute(query)
    cases = result.scalars().all()
    return [CaseListResponse.model_validate(c) for c in cases]


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new case with customer and alert information.
    All text inputs are sanitized to prevent prompt injection.
    """
    case = Case(
        customer_id=sanitize_input(case_data.customer_id),
        customer_name=sanitize_input(case_data.customer_name),
        customer_type=case_data.customer_type,
        customer_risk_rating=case_data.customer_risk_rating,
        kyc_id_type=case_data.kyc_id_type,
        kyc_id_number=case_data.kyc_id_number,
        kyc_country=case_data.kyc_country,
        kyc_occupation=sanitize_input(case_data.kyc_occupation) if case_data.kyc_occupation else None,
        kyc_onboarding_date=case_data.kyc_onboarding_date,
        account_number=case_data.account_number,
        account_type=case_data.account_type,
        account_open_date=case_data.account_open_date,
        account_balance=case_data.account_balance,
        account_currency=case_data.account_currency,
        alert_id=case_data.alert_id,
        alert_date=case_data.alert_date,
        alert_type=case_data.alert_type,
        alert_score=case_data.alert_score,
        notes=sanitize_input(case_data.notes) if case_data.notes else None,
        historical_avg_monthly_volume=case_data.historical_avg_monthly_volume,
        historical_avg_transaction_size=case_data.historical_avg_transaction_size,
        historical_counterparty_count=case_data.historical_counterparty_count,
        historical_sar_count=case_data.historical_sar_count,
        composite_risk_score=case_data.composite_risk_score,
        network_risk_score=case_data.network_risk_score,
        behavioral_risk_score=case_data.behavioral_risk_score,
        graph_analysis=sanitize_input(case_data.graph_analysis) if case_data.graph_analysis else None,
    )
    db.add(case)
    await db.flush()

    # Immutable log entry
    await write_immutable_log(
        db=db,
        entity_type="case",
        entity_id=str(case.id),
        action="case_created",
        actor_id=SYSTEM_ACTOR,
        details=f"Customer: {case.customer_name} | Alert: {case.alert_id}",
    )

    return CaseResponse.model_validate(case)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single case by ID.
    Enforces case-level isolation — only returns the requested case.
    """
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    return CaseResponse.model_validate(case)


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: UUID,
    updates: CaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update case fields (status, notes, risk rating, etc.)."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if isinstance(value, str):
            value = sanitize_input(value)
        if field == "status":
            value = CaseStatus(value)
        setattr(case, field, value)

    await write_immutable_log(
        db=db,
        entity_type="case",
        entity_id=str(case.id),
        action="case_updated",
        actor_id=SYSTEM_ACTOR,
        details=f"Fields updated: {', '.join(update_data.keys())}",
    )

    await db.flush()
    return CaseResponse.model_validate(case)
