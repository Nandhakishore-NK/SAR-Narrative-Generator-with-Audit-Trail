"""
Transaction Schemas — Transaction ingestion and response DTOs.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    transaction_ref: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: str = Field(default="INR", max_length=10)
    transaction_date: datetime
    transaction_type: Optional[str] = None
    direction: Optional[str] = Field(None, pattern="^(inbound|outbound)$")
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_bank: Optional[str] = None
    country: Optional[str] = None
    purpose: Optional[str] = None
    is_flagged: bool = False


class TransactionBulkCreate(BaseModel):
    """Accepts multiple transactions for a case in a single request."""
    transactions: List[TransactionCreate] = Field(..., min_length=1)


class TransactionResponse(BaseModel):
    id: UUID
    case_id: UUID
    transaction_ref: Optional[str] = None
    amount: float
    currency: str
    transaction_date: datetime
    transaction_type: Optional[str] = None
    direction: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_bank: Optional[str] = None
    country: Optional[str] = None
    purpose: Optional[str] = None
    is_flagged: bool
    created_at: datetime

    model_config = {"from_attributes": True}
