"""
Override Service — Evidence-backed manual override governance enforcement.

Governance rules (NON-NEGOTIABLE):
1. EVERY override MUST have:
   - Valid override reason code
   - Supporting evidence reference (non-empty)
   - Original sentence hash must match current sentence hash

2. For HIGH or CRITICAL severity narratives:
   - Supervisor approval is MANDATORY before the override takes effect
   - Analyst CANNOT approve their own override

3. ALL override actions are logged immutably

4. Override does NOT take effect until approval_status = 'approved'
   (or if severity is LOW/MEDIUM, auto-approved on submission)
"""

from uuid import UUID
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.narrative_sentence import NarrativeSentence
from app.models.sar_narrative import SarNarrative
from app.models.override import Override, ApprovalStatus, OverrideReasonCode
from app.models.user import User, UserRole
from app.services.hash_service import hash_sentence
from app.services.audit_service import write_immutable_log


async def validate_and_create_override(
    db: AsyncSession,
    sentence_id: UUID,
    modified_text: str,
    reason_code: str,
    evidence_reference: str,
    analyst: User,
) -> Override:
    """
    Create an override request with full governance validation.
    
    Validates:
    - Sentence exists and belongs to an active narrative
    - Reason code is valid
    - Evidence reference is non-empty
    - Original hash matches current sentence
    - Determines if supervisor approval is required
    """
    # 1. Fetch the sentence
    result = await db.execute(
        select(NarrativeSentence).where(NarrativeSentence.id == sentence_id)
    )
    sentence = result.scalar_one_or_none()
    if not sentence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sentence not found"
        )

    # 2. Fetch the parent narrative to check severity
    result = await db.execute(
        select(SarNarrative).where(SarNarrative.id == sentence.narrative_id)
    )
    narrative = result.scalar_one_or_none()
    if not narrative or not narrative.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Override can only be applied to active narratives"
        )

    # 3. Validate reason code
    try:
        valid_reason = OverrideReasonCode(reason_code)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid override reason code: {reason_code}"
        )

    # 4. Validate evidence reference is substantive
    if not evidence_reference or len(evidence_reference.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence reference must be substantive (minimum 10 characters)"
        )

    # 5. Generate hashes
    original_hash = sentence.sentence_hash
    modified_hash = hash_sentence(modified_text)

    # 6. Check if text actually changed
    if original_hash == modified_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modified text is identical to original — no override needed"
        )

    # 7. Determine approval status based on severity
    severity = narrative.severity.upper()
    if severity in ("HIGH", "CRITICAL"):
        # Supervisor approval mandatory
        approval = ApprovalStatus.pending
    else:
        # LOW/MEDIUM severity: auto-approved
        approval = ApprovalStatus.approved

    # 8. Create override record
    override = Override(
        sentence_id=sentence_id,
        original_hash=original_hash,
        modified_text=modified_text,
        modified_hash=modified_hash,
        override_reason_code=valid_reason,
        evidence_reference=evidence_reference,
        analyst_id=analyst.id,
        approval_status=approval,
    )
    db.add(override)
    await db.flush()

    # 9. Log immutably
    await write_immutable_log(
        db=db,
        entity_type="override",
        entity_id=str(override.id),
        action="override_submitted",
        actor_id=str(analyst.id),
        details=f"Sentence {sentence_id} | Reason: {reason_code} | Severity: {severity}",
    )

    # 10. If auto-approved, apply the override immediately
    if approval == ApprovalStatus.approved:
        await _apply_override(db, override, sentence)

    return override


async def approve_override(
    db: AsyncSession,
    override_id: UUID,
    supervisor: User,
    approval_status: str,
    approval_notes: Optional[str] = None,
) -> Override:
    """
    Supervisor approval/rejection of an override.
    
    Enforces:
    - Only supervisors and admins can approve
    - Analyst cannot approve their own override
    - Override must be in pending status
    """
    # 1. Fetch override
    result = await db.execute(select(Override).where(Override.id == override_id))
    override = result.scalar_one_or_none()
    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Override not found"
        )

    # 2. Check override is pending
    if override.approval_status != ApprovalStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Override already {override.approval_status.value}"
        )

    # 3. Enforce role: must be supervisor or admin
    if supervisor.role not in (UserRole.supervisor, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only supervisors or admins can approve overrides"
        )

    # 4. Analyst cannot approve own override
    if override.analyst_id == supervisor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst cannot approve their own override"
        )

    # 5. Update override
    override.supervisor_id = supervisor.id
    override.approval_status = ApprovalStatus(approval_status)
    override.approval_notes = approval_notes

    # 6. If approved, apply the text change
    if override.approval_status == ApprovalStatus.approved:
        result = await db.execute(
            select(NarrativeSentence).where(NarrativeSentence.id == override.sentence_id)
        )
        sentence = result.scalar_one_or_none()
        if sentence:
            await _apply_override(db, override, sentence)

    # 7. Log immutably
    action = "override_approved" if approval_status == "approved" else "override_rejected"
    await write_immutable_log(
        db=db,
        entity_type="override",
        entity_id=str(override.id),
        action=action,
        actor_id=str(supervisor.id),
        details=f"Notes: {approval_notes or 'N/A'}",
    )

    await db.flush()
    return override


async def _apply_override(
    db: AsyncSession,
    override: Override,
    sentence: NarrativeSentence,
) -> None:
    """
    Apply an approved override to the sentence.
    Updates the sentence text and hash.
    """
    # Verify hash hasn't changed since override was submitted (concurrent edit detection)
    if sentence.sentence_hash != override.original_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sentence has been modified since override was submitted. Hash mismatch detected."
        )

    sentence.sentence_text = override.modified_text
    sentence.sentence_hash = override.modified_hash

    # Log the sentence modification
    await write_immutable_log(
        db=db,
        entity_type="narrative_sentence",
        entity_id=str(sentence.id),
        action="sentence_modified",
        actor_id=str(override.analyst_id),
        details=f"Override {override.id} applied | Old hash: {override.original_hash[:16]}... | New hash: {override.modified_hash[:16]}...",
    )
