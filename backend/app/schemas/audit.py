"""
Audit Schemas — DTOs for audit trail and immutable log queries.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class AuditTimelineEntry(BaseModel):
    id: UUID
    entity_type: str
    entity_id: str
    action: str
    actor_id: Optional[str] = None
    details: Optional[str] = None
    hash_signature: str
    previous_hash: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class AuditTimelineResponse(BaseModel):
    case_id: UUID
    entries: List[AuditTimelineEntry]
    chain_valid: bool  # Whether hash chain integrity is intact
