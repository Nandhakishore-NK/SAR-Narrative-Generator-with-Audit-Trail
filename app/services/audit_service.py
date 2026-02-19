"""
Audit Trail Service - Complete immutable audit logging for SAR system.
Every action, decision, and data access is logged with full context.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.models.database import AuditLog, SARCase, SessionLocal

logger = logging.getLogger(__name__)

ACTION_CATEGORIES = {
    # SAR Generation
    "SAR_GENERATION_STARTED": "GENERATION",
    "SAR_GENERATION_COMPLETED": "GENERATION",
    "SAR_GENERATION_FAILED": "GENERATION",
    # Edits
    "NARRATIVE_EDITED": "EDIT",
    "NARRATIVE_SAVED": "EDIT",
    # Approvals
    "SAR_APPROVED": "APPROVAL",
    "SAR_REJECTED": "APPROVAL",
    "SAR_SUBMITTED": "APPROVAL",
    "SAR_FILED": "APPROVAL",
    # Data Access
    "CASE_VIEWED": "ACCESS",
    "CASE_CREATED": "ACCESS",
    "CUSTOMER_DATA_ACCESSED": "ACCESS",
    "TRANSACTION_DATA_ACCESSED": "ACCESS",
    "AUDIT_LOG_VIEWED": "ACCESS",
    # Authentication
    "USER_LOGIN": "AUTH",
    "USER_LOGOUT": "AUTH",
    "USER_LOGIN_FAILED": "AUTH",
    "USER_CREATED": "AUTH",
    # Alerts
    "ALERT_TRIGGERED": "ALERT",
    "ALERT_ACKNOWLEDGED": "ALERT",
    "ALERT_ESCALATED": "ALERT",
    # System
    "SYSTEM_CONFIG_CHANGED": "SYSTEM",
    "DATA_EXPORTED": "SYSTEM",
}


class AuditService:

    def log(
        self,
        action: str,
        case_id: Optional[str] = None,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        reasoning_trace: Optional[str] = None,
        data_sources_used: Optional[List[str]] = None,
        rules_matched: Optional[List[str]] = None,
        llm_prompt_hash: Optional[str] = None,
        llm_model_used: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Optional[AuditLog]:
        """Create an immutable audit log entry."""
        db: Session = SessionLocal()
        try:
            entry = AuditLog(
                case_id=case_id,
                user_id=user_id,
                action=action,
                action_category=ACTION_CATEGORIES.get(action, "GENERAL"),
                details=details or {},
                reasoning_trace=reasoning_trace,
                data_sources_used=data_sources_used or [],
                rules_matched=rules_matched or [],
                llm_prompt_hash=llm_prompt_hash,
                llm_model_used=llm_model_used,
                ip_address=ip_address,
                success=success,
                error_message=error_message,
                created_at=datetime.utcnow()
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            logger.info(f"AUDIT [{entry.action_category}] {action} - Case: {case_id} User: {user_id}")
            return entry
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    def log_generation(
        self,
        case_id: str,
        user_id: int,
        generation_result,
        hosting_env: str = "on-premises"
    ):
        """Log a SAR narrative generation event with full AI reasoning."""
        audit = generation_result.audit_trail
        reasoning = self._format_reasoning_trace(
            risk_indicators=audit.get("risk_indicators_extracted", []),
            typologies=audit.get("typologies_matched", []),
            confidence=audit.get("confidence_level", "MEDIUM"),
            data_sources=audit.get("data_sources_used", []),
            rag_templates=audit.get("rag_templates_used", []),
            rag_regulations=audit.get("rag_regulations_used", []),
            model=generation_result.model_used,
            generation_time=generation_result.generation_time_seconds,
            tokens_used=generation_result.tokens_used,
            hosting_env=hosting_env
        )
        self.log(
            action="SAR_GENERATION_COMPLETED",
            case_id=case_id,
            user_id=user_id,
            details={
                "model_used": generation_result.model_used,
                "generation_time_seconds": generation_result.generation_time_seconds,
                "tokens_used": generation_result.tokens_used,
                "confidence_level": generation_result.confidence_level,
                "typologies_matched": generation_result.typologies_matched,
                "rag_templates_used": audit.get("rag_templates_used", []),
                "rag_regulations_used": audit.get("rag_regulations_used", []),
                "risk_indicators_count": len(audit.get("risk_indicators_extracted", [])),
                "hosting_environment": hosting_env
            },
            reasoning_trace=reasoning,
            data_sources_used=generation_result.data_sources_used,
            rules_matched=generation_result.rules_matched,
            llm_prompt_hash=generation_result.prompt_hash,
            llm_model_used=generation_result.model_used,
            success=True
        )

    def log_edit(
        self,
        case_id: str,
        user_id: int,
        username: str,
        original_text: str,
        edited_text: str,
        change_summary: Optional[str] = None
    ):
        """Log narrative edit with diff summary."""
        orig_len = len(original_text)
        edit_len = len(edited_text)
        change_pct = abs(edit_len - orig_len) / max(orig_len, 1) * 100
        self.log(
            action="NARRATIVE_EDITED",
            case_id=case_id,
            user_id=user_id,
            details={
                "editor": username,
                "original_length_chars": orig_len,
                "edited_length_chars": edit_len,
                "change_percentage": round(change_pct, 2),
                "change_summary": change_summary or f"Manual edit: {change_pct:.1f}% content changed"
            },
            reasoning_trace=f"Human analyst '{username}' edited the SAR narrative. "
                            f"Original: {orig_len} chars. Edited: {edit_len} chars. "
                            f"Change magnitude: {change_pct:.1f}%",
            success=True
        )

    def log_approval(self, case_id: str, user_id: int, username: str, approved: bool, reason: Optional[str] = None):
        """Log SAR approval or rejection."""
        action = "SAR_APPROVED" if approved else "SAR_REJECTED"
        self.log(
            action=action,
            case_id=case_id,
            user_id=user_id,
            details={
                "decision_by": username,
                "decision": "APPROVED" if approved else "REJECTED",
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            },
            reasoning_trace=f"SAR {'approved' if approved else 'rejected'} by {username}. "
                            f"Reason: {reason or 'Not provided'}",
            success=True
        )

    def get_case_audit_trail(self, case_id: str) -> List[AuditLog]:
        """Retrieve full audit trail for a case."""
        db: Session = SessionLocal()
        try:
            logs = db.query(AuditLog)\
                .filter(AuditLog.case_id == case_id)\
                .order_by(AuditLog.created_at.asc())\
                .all()
            return logs
        finally:
            db.close()

    def get_recent_audit_logs(self, limit: int = 100, category: Optional[str] = None) -> List[AuditLog]:
        """Get recent audit logs, optionally filtered by category."""
        db: Session = SessionLocal()
        try:
            q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
            if category:
                q = q.filter(AuditLog.action_category == category)
            return q.limit(limit).all()
        finally:
            db.close()

    def get_audit_stats(self) -> Dict[str, Any]:
        """Get aggregate audit statistics."""
        db: Session = SessionLocal()
        try:
            total = db.query(AuditLog).count()
            generations = db.query(AuditLog).filter(AuditLog.action_category == "GENERATION").count()
            approvals = db.query(AuditLog).filter(AuditLog.action == "SAR_APPROVED").count()
            rejections = db.query(AuditLog).filter(AuditLog.action == "SAR_REJECTED").count()
            edits = db.query(AuditLog).filter(AuditLog.action == "NARRATIVE_EDITED").count()
            return {
                "total_events": total,
                "generation_events": generations,
                "approval_events": approvals,
                "rejection_events": rejections,
                "edit_events": edits
            }
        finally:
            db.close()

    def _format_reasoning_trace(
        self,
        risk_indicators: List[str],
        typologies: List[str],
        confidence: str,
        data_sources: List[str],
        rag_templates: List[str],
        rag_regulations: List[str],
        model: str,
        generation_time: float,
        tokens_used: Optional[int],
        hosting_env: str
    ) -> str:
        """Format a human-readable reasoning trace for the audit log."""
        lines = [
            "=== AI REASONING TRACE ===",
            f"Timestamp: {datetime.utcnow().isoformat()}",
            f"Model: {model}",
            f"Generation time: {generation_time:.2f}s",
            f"Tokens used: {tokens_used or 'N/A'}",
            f"Hosting environment: {hosting_env}",
            "",
            "--- RISK INDICATORS EXTRACTED ---",
        ]
        for indicator in risk_indicators:
            lines.append(f"  [!] {indicator}")
        lines.extend(["", "--- TYPOLOGIES MATCHED ---"])
        for typo in typologies or ["Not yet extracted"]:
            lines.append(f"  [*] {typo}")
        lines.extend(["", f"--- CONFIDENCE LEVEL: {confidence} ---", ""])
        lines.extend(["--- RAG CONTEXT USED ---"])
        lines.append(f"  Templates: {', '.join(rag_templates) or 'None'}")
        lines.append(f"  Regulations: {', '.join(rag_regulations) or 'None'}")
        lines.extend(["", "--- DATA SOURCES ---"])
        for src in data_sources or ["Customer KYC", "Transaction Alert", "Transaction Data"]:
            lines.append(f"  [>>] {src}")
        return "\n".join(lines)


audit_service = AuditService()
