"""
Transactions API — Transaction ingestion and query endpoints.

Supports:
- Single and bulk transaction creation
- Query by case ID
- Rule trigger management
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.case import Case
from app.models.transaction import Transaction
from app.models.rule_trigger import RuleTrigger
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionBulkCreate, TransactionResponse
from app.schemas.rule_trigger import RuleTriggerCreate, RuleTriggerBulkCreate, RuleTriggerResponse
from app.middleware.role_guard import require_analyst
from app.services.audit_service import write_immutable_log

router = APIRouter()


@router.post(
    "/cases/{case_id}/transactions",
    response_model=List[TransactionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_transactions(
    case_id: UUID,
    payload: TransactionBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Bulk-add transactions to a case.
    Validates that the case exists before inserting.
    """
    # Verify case exists
    result = await db.execute(select(Case).where(Case.id == case_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    created = []
    for txn_data in payload.transactions:
        txn = Transaction(
            case_id=case_id,
            transaction_ref=txn_data.transaction_ref,
            amount=txn_data.amount,
            currency=txn_data.currency,
            transaction_date=txn_data.transaction_date,
            transaction_type=txn_data.transaction_type,
            direction=txn_data.direction,
            counterparty_name=txn_data.counterparty_name,
            counterparty_account=txn_data.counterparty_account,
            counterparty_bank=txn_data.counterparty_bank,
            country=txn_data.country,
            purpose=txn_data.purpose,
            is_flagged=txn_data.is_flagged,
        )
        db.add(txn)
        created.append(txn)

    await db.flush()

    await write_immutable_log(
        db=db,
        entity_type="case",
        entity_id=str(case_id),
        action="transactions_added",
        actor_id=str(current_user.id),
        details=f"Added {len(created)} transactions",
    )

    return [TransactionResponse.model_validate(t) for t in created]


@router.get("/cases/{case_id}/transactions", response_model=List[TransactionResponse])
async def get_case_transactions(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """Get all transactions for a case."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.case_id == case_id)
        .order_by(Transaction.transaction_date.asc())
    )
    transactions = result.scalars().all()
    return [TransactionResponse.model_validate(t) for t in transactions]


@router.post(
    "/cases/{case_id}/rule-triggers",
    response_model=List[RuleTriggerResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_rule_triggers(
    case_id: UUID,
    payload: RuleTriggerBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """Bulk-add rule triggers to a case."""
    # Verify case exists
    result = await db.execute(select(Case).where(Case.id == case_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    created = []
    for trigger_data in payload.triggers:
        trigger = RuleTrigger(
            case_id=case_id,
            rule_code=trigger_data.rule_code,
            rule_description=trigger_data.rule_description,
            threshold_value=trigger_data.threshold_value,
            actual_value=trigger_data.actual_value,
            breached=trigger_data.breached,
            typology_code=trigger_data.typology_code,
            typology_description=trigger_data.typology_description,
        )
        db.add(trigger)
        created.append(trigger)

    await db.flush()

    await write_immutable_log(
        db=db,
        entity_type="case",
        entity_id=str(case_id),
        action="rule_triggers_added",
        actor_id=str(current_user.id),
        details=f"Added {len(created)} rule triggers",
    )

    return [RuleTriggerResponse.model_validate(t) for t in created]


@router.get("/cases/{case_id}/rule-triggers", response_model=List[RuleTriggerResponse])
async def get_case_rule_triggers(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """Get all rule triggers for a case."""
    result = await db.execute(
        select(RuleTrigger).where(RuleTrigger.case_id == case_id)
    )
    triggers = result.scalars().all()
    return [RuleTriggerResponse.model_validate(t) for t in triggers]
