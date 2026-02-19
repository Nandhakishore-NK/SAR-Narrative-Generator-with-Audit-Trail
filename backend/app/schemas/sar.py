"""
SAR Generation Schemas — Request/response DTOs for SAR narrative generation.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class SarGenerateRequest(BaseModel):
    """Triggers SAR narrative generation for a case."""
    case_id: UUID


class SentenceBreakdown(BaseModel):
    """Individual sentence with evidence mapping."""
    sentence_id: UUID
    sentence_index: int
    sentence_text: str
    sentence_hash: str
    confidence_level: str
    supporting_transaction_ids: List[str] = []
    rule_reference: Optional[str] = None
    threshold_reference: Optional[str] = None
    typology_reference: Optional[str] = None
    graph_reference: Optional[str] = None


class SarNarrativeResponse(BaseModel):
    """Complete SAR generation response."""
    narrative_id: UUID
    case_id: UUID
    narrative_text: str
    version: int
    severity: str
    is_active: bool
    created_by: UUID
    created_at: datetime
    sentences: List[SentenceBreakdown] = []

    model_config = {"from_attributes": True}


class AuditTrailResponse(BaseModel):
    """Audit trail JSON response."""
    id: UUID
    case_id: UUID
    audit_json: Dict[str, Any]
    model_version: str
    narrative_version: int
    timestamp: datetime

    model_config = {"from_attributes": True}
