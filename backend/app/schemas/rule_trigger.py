"""
Rule Trigger Schemas — AML rule trigger DTOs.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel, Field


class RuleTriggerCreate(BaseModel):
    rule_code: str = Field(..., min_length=1, max_length=50)
    rule_description: Optional[str] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    breached: bool = False
    typology_code: Optional[str] = None
    typology_description: Optional[str] = None


class RuleTriggerBulkCreate(BaseModel):
    triggers: List[RuleTriggerCreate] = Field(..., min_length=1)


class RuleTriggerResponse(BaseModel):
    id: UUID
    case_id: UUID
    rule_code: str
    rule_description: Optional[str] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    breached: bool
    typology_code: Optional[str] = None
    typology_description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
