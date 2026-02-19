"""
Case Schemas — Case creation, update, and response DTOs.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_type: Optional[str] = None
    customer_risk_rating: Optional[str] = None

    # KYC
    kyc_id_type: Optional[str] = None
    kyc_id_number: Optional[str] = None
    kyc_country: Optional[str] = None
    kyc_occupation: Optional[str] = None
    kyc_onboarding_date: Optional[datetime] = None

    # Account
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    account_open_date: Optional[datetime] = None
    account_balance: Optional[float] = None
    account_currency: Optional[str] = "USD"

    # Alert
    alert_id: Optional[str] = None
    alert_date: Optional[datetime] = None
    alert_type: Optional[str] = None
    alert_score: Optional[float] = None

    # Notes
    notes: Optional[str] = None

    # Historical
    historical_avg_monthly_volume: Optional[float] = None
    historical_avg_transaction_size: Optional[float] = None
    historical_counterparty_count: Optional[int] = None
    historical_sar_count: Optional[int] = 0

    # Risk scores
    composite_risk_score: Optional[float] = None
    network_risk_score: Optional[float] = None
    behavioral_risk_score: Optional[float] = None

    # Graph
    graph_analysis: Optional[str] = None


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    customer_risk_rating: Optional[str] = None
    composite_risk_score: Optional[float] = None
    graph_analysis: Optional[str] = None


class CaseResponse(BaseModel):
    id: UUID
    customer_id: str
    customer_name: str
    customer_type: Optional[str] = None
    customer_risk_rating: Optional[str] = None
    kyc_id_type: Optional[str] = None
    kyc_id_number: Optional[str] = None
    kyc_country: Optional[str] = None
    kyc_occupation: Optional[str] = None
    kyc_onboarding_date: Optional[datetime] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    account_open_date: Optional[datetime] = None
    account_balance: Optional[float] = None
    account_currency: Optional[str] = None
    alert_id: Optional[str] = None
    alert_date: Optional[datetime] = None
    alert_type: Optional[str] = None
    alert_score: Optional[float] = None
    status: str
    notes: Optional[str] = None
    historical_avg_monthly_volume: Optional[float] = None
    historical_avg_transaction_size: Optional[float] = None
    historical_counterparty_count: Optional[int] = None
    historical_sar_count: Optional[int] = None
    composite_risk_score: Optional[float] = None
    network_risk_score: Optional[float] = None
    behavioral_risk_score: Optional[float] = None
    graph_analysis: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    id: UUID
    customer_id: str
    customer_name: str
    customer_risk_rating: Optional[str] = None
    alert_id: Optional[str] = None
    alert_type: Optional[str] = None
    status: str
    composite_risk_score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}
