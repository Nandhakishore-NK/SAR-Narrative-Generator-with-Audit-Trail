"""
Override Schemas — DTOs for evidence-backed manual override governance.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field


class OverrideCreate(BaseModel):
    """
    Submit an override request.
    All fields are mandatory per governance rules.
    """
    sentence_id: UUID
    modified_text: str = Field(..., min_length=1)
    override_reason_code: str = Field(
        ...,
        pattern="^(factual_correction|additional_evidence|regulatory_update|typology_reclassification|risk_reassessment|data_quality_issue|supervisor_directed)$",
    )
    evidence_reference: str = Field(..., min_length=1)


class OverrideApproval(BaseModel):
    """Supervisor approval/rejection of an override."""
    approval_status: str = Field(..., pattern="^(approved|rejected)$")
    approval_notes: Optional[str] = None


class OverrideResponse(BaseModel):
    id: UUID
    sentence_id: UUID
    original_hash: str
    modified_text: str
    modified_hash: str
    override_reason_code: str
    evidence_reference: str
    analyst_id: UUID
    supervisor_id: Optional[UUID] = None
    approval_status: str
    approval_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
