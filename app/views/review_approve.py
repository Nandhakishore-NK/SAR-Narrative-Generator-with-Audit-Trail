"""Review & Approve Page - Human analyst review of AI-generated SAR narratives"""
import streamlit as st
from datetime import datetime
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.models.database import (
    SARCase, NarrativeVersion, CustomerProfile, TransactionAlert,
    CaseStatus, SessionLocal
)
from app.services.audit_service import audit_service
from app.services.alert_service import alert_service
from app.utils.auth import has_permission


def load_review_cases():
    db: Session = SessionLocal()
    try:
        return db.query(SARCase).filter(
            SARCase.status.in_([CaseStatus.IN_REVIEW, CaseStatus.OPEN])
        ).order_by(SARCase.created_at.desc()).all()
    finally:
        db.close()


def get_case_details(case_id: str):
    db: Session = SessionLocal()
    try:
        case = db.query(SARCase).filter(SARCase.case_id == case_id).first()
        if not case:
            return None, None, None
        customer = db.query(CustomerProfile).filter(CustomerProfile.customer_id == case.customer_id).first()
        alert = db.query(TransactionAlert).filter(TransactionAlert.alert_id == case.alert_id).first() if case.alert_id else None
        return case, customer, alert
    finally:
        db.close()


def save_edited_narrative(case_id: str, new_narrative: str, username: str, user_id: int) -> bool:
    db: Session = SessionLocal()
    try:
        case = db.query(SARCase).filter(SARCase.case_id == case_id).first()
        if not case:
            return False
        original = case.edited_narrative or case.generated_narrative or ""
        case.edited_narrative = new_narrative
        case.narrative_version = (case.narrative_version or 1) + 1
        case.updated_at = datetime.utcnow()
        version = NarrativeVersion(
            case_id=case_id,
            version_number=case.narrative_version,
            narrative_text=new_narrative,
            change_type="EDIT",
            change_summary=f"Edited by analyst {username}",
            changed_by=username,
            created_at=datetime.utcnow()
        )
        db.add(version)
        db.commit()
        audit_service.log_edit(case_id, user_id, username, original, new_narrative)
        return True
    except Exception as e:
        db.rollback()
        return False
    finally:
        db.close()


def approve_case(case_id: str, user_id: int, username: str, notes: str) -> bool:
    db: Session = SessionLocal()
    try:
        case = db.query(SARCase).filter(SARCase.case_id == case_id).first()
        if not case:
            return False
        final_text = case.edited_narrative or case.generated_narrative
        case.final_narrative = final_text
        case.status = CaseStatus.APPROVED
        case.approved_by = username
        case.analyst_notes = notes
        case.updated_at = datetime.utcnow()
        version = NarrativeVersion(
            case_id=case_id,
            version_number=(case.narrative_version or 1) + 1,
            narrative_text=final_text or "",
            change_type="APPROVED",
            change_summary=f"Approved by {username}. Notes: {notes}",
            changed_by=username,
            created_at=datetime.utcnow()
        )
        db.add(version)
        db.commit()
        audit_service.log_approval(case_id, user_id, username, True, notes)
        alert_service.create_alert(
            "SAR_APPROVED",
            f"SAR Case {case_id} has been approved by {username} and is ready for filing.",
            case_id=case_id
        )
        return True
    except Exception as e:
        db.rollback()
        return False
    finally:
        db.close()


def reject_case(case_id: str, user_id: int, username: str, reason: str) -> bool:
    db: Session = SessionLocal()
    try:
        case = db.query(SARCase).filter(SARCase.case_id == case_id).first()
        if not case:
            return False
        case.status = CaseStatus.REJECTED
        case.rejection_reason = reason
        case.updated_at = datetime.utcnow()
        db.commit()
        audit_service.log_approval(case_id, user_id, username, False, reason)
        alert_service.create_alert(
            "SAR_REJECTED",
            f"SAR Case {case_id} rejected by {username}. Reason: {reason}",
            case_id=case_id, severity="MEDIUM"
        )
        return True
    except Exception as e:
        db.rollback()
        return False
    finally:
        db.close()


def file_sar(case_id: str, user_id: int, username: str, sar_ref: str) -> bool:
    db: Session = SessionLocal()
    try:
        case = db.query(SARCase).filter(SARCase.case_id == case_id).first()
        if not case:
            return False
        case.status = CaseStatus.FILED
        case.sar_reference = sar_ref
        case.filed_at = datetime.utcnow()
        case.updated_at = datetime.utcnow()
        db.commit()
        audit_service.log(
            "SAR_FILED", case_id=case_id, user_id=user_id,
            details={"filed_by": username, "sar_reference": sar_ref, "filed_at": datetime.utcnow().isoformat()}
        )
        alert_service.create_alert(
            "SAR_FILED",
            f"SAR Case {case_id} has been filed with FIU-IND. Reference: {sar_ref}",
            case_id=case_id
        )
        return True
    except Exception as e:
        db.rollback()
        return False
    finally:
        db.close()


def show_review_approve(user: dict):
    st.markdown("""
    <div class="app-header">
        <div>
            <h2 style="margin:0;color:white;">🔍 Review & Approve SAR Narratives</h2>
            <p style="margin:0;opacity:0.8;font-size:0.85rem;">Human analyst review, editing, and approval workflow</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    cases = load_review_cases()
    if not cases:
        st.info("📭 No cases pending review. Generate a SAR narrative to get started.")
        if st.button("➕ Generate New SAR"):
            st.session_state["page"] = "generate"
            st.rerun()
        return
    # pre-select from session if coming from generator page
    pre_selected = st.session_state.pop("review_case_id", None)
    case_options = {f"{c.case_id} | {c.customer_id} | [{c.status.value}] | {c.created_at.strftime('%d/%m/%Y %H:%M') if c.created_at else ''}": c for c in cases}
    # Find index for pre-selected
    default_idx = 0
    if pre_selected:
        for i, k in enumerate(case_options.keys()):
            if pre_selected in k:
                default_idx = i
                break
    selected_label = st.selectbox("Select Case to Review", list(case_options.keys()), index=default_idx)
    selected_case_obj = case_options[selected_label]
    case, customer, alert = get_case_details(selected_case_obj.case_id)
    if not case:
        st.error("Could not load case details.")
        return
    # Case header
    status_colors = {
        "OPEN": "#e65100", "IN_REVIEW": "#1565c0", "APPROVED": "#2e7d32",
        "FILED": "#00205b", "REJECTED": "#c62828", "CLOSED": "#607d8b"
    }
    sc = status_colors.get(case.status.value, "#607d8b")
    st.markdown(f"""
    <div style="background:#f5f7fb;border:1px solid #d0d7de;border-radius:10px;padding:14px 18px;margin:10px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <span style="font-size:1.1rem;font-weight:700;">📋 {case.case_id}</span>
                &nbsp;&nbsp;
                <span style="background:{sc};color:white;padding:2px 10px;border-radius:10px;font-size:0.78rem;font-weight:600;">{case.status.value}</span>
            </div>
            <div style="color:#607d8b;font-size:0.82rem;">
                Created: {case.created_at.strftime('%d %b %Y %H:%M') if case.created_at else 'N/A'}
                {f' | Approved by: {case.approved_by}' if case.approved_by else ''}
            </div>
        </div>
        <div style="margin-top:8px;font-size:0.86rem;color:#555;">
            Customer: <b>{customer.full_name if customer else case.customer_id}</b>
            {f' | Alert: {case.alert_id}' if case.alert_id else ''}
            {f' | Narrative version: v{case.narrative_version}' if case.narrative_version else ''}
            {f' | Model: {case.generation_metadata.get("model", "N/A") if case.generation_metadata else "N/A"}' }
        </div>
    </div>
    """, unsafe_allow_html=True)
    # Tabs
    edit_tab, audit_tab, versions_tab = st.tabs(["✏️ Narrative (Edit & Approve)", "🔍 Audit Trail", "📋 Version History"])

    # ===== EDIT TAB =====
    with edit_tab:
        current_text = case.edited_narrative or case.generated_narrative or ""
        col_info, col_actions = st.columns([3, 1])
        with col_info:
            st.markdown("##### ✏️ Human Review — Edit the AI-generated narrative below")
            st.caption("You may edit any part of this narrative. All changes are tracked in the audit trail.")
            if case.status in [CaseStatus.APPROVED, CaseStatus.FILED, CaseStatus.CLOSED]:
                st.info(f"This case has been {case.status.value}. Showing final narrative (read-only).")
                st.markdown(f'<div class="narrative-box">{current_text}</div>', unsafe_allow_html=True)
            else:
                edited_text = st.text_area(
                    "SAR Narrative",
                    value=current_text,
                    height=520,
                    label_visibility="collapsed"
                )
                save_edit = st.button("💾 Save Edits", use_container_width=False)
                if save_edit:
                    if edited_text != current_text:
                        if save_edited_narrative(case.case_id, edited_text, user["username"], user["id"]):
                            st.success("✅ Edits saved successfully and logged in audit trail.")
                            st.rerun()
                        else:
                            st.error("Failed to save edits.")
                    else:
                        st.info("No changes detected.")
        with col_actions:
            st.markdown("##### Decision Actions")
            with st.container(border=True):
                if case.status not in [CaseStatus.APPROVED, CaseStatus.FILED, CaseStatus.CLOSED, CaseStatus.REJECTED]:
                    if has_permission(user["role"], "approve_sar"):
                        approval_notes = st.text_area("Approval Notes", height=80, placeholder="Add any notes...")
                        if st.button("✅ Approve SAR", use_container_width=True, type="primary"):
                            if approve_case(case.case_id, user["id"], user["username"], approval_notes):
                                st.success("SAR Approved!")
                                st.rerun()
                        st.markdown("---")
                        rejection_reason = st.text_area("Rejection Reason", height=60, placeholder="Reason for rejection (required)")
                        if st.button("❌ Reject SAR", use_container_width=True):
                            if not rejection_reason:
                                st.error("Please provide a rejection reason.")
                            else:
                                if reject_case(case.case_id, user["id"], user["username"], rejection_reason):
                                    st.error("SAR Rejected.")
                                    st.rerun()
                    else:
                        st.warning("You need SUPERVISOR or ADMIN role to approve/reject SARs.")
                elif case.status == CaseStatus.APPROVED:
                    if has_permission(user["role"], "file_sar"):
                        st.success("✅ Approved — Ready for Filing")
                        sar_ref = st.text_input("FIU-IND STR Reference", placeholder="e.g. STR-2024-XXXXX")
                        if st.button("📤 File with FIU-IND", use_container_width=True, type="primary"):
                            if not sar_ref:
                                st.error("Please enter the FIU-IND STR reference.")
                            else:
                                if file_sar(case.case_id, user["id"], user["username"], sar_ref):
                                    st.success(f"SAR Filed! Reference: {sar_ref}")
                                    st.rerun()
                elif case.status == CaseStatus.FILED:
                    st.success(f"📤 FILED — Ref: {case.sar_reference}")
                elif case.status == CaseStatus.REJECTED:
                    st.error(f"❌ REJECTED: {case.rejection_reason}")
            # Generation metadata
            if case.generation_metadata:
                st.markdown("---")
                st.markdown("**Generation Info**")
                meta = case.generation_metadata
                st.caption(f"Model: {meta.get('model', 'N/A')}")
                st.caption(f"Confidence: {meta.get('confidence_level', 'N/A')}")
                st.caption(f"Time: {meta.get('generation_time', 0):.1f}s")
                st.caption(f"Env: {meta.get('hosting_environment', 'N/A')}")
            # Download
            if current_text:
                st.markdown("---")
                st.download_button(
                    "⬇️ Download Final Narrative",
                    current_text,
                    file_name=f"{case.case_id}_final_narrative.txt",
                    mime="text/plain",
                    use_container_width=True
                )

    # ===== AUDIT TAB =====
    with audit_tab:
        st.markdown("#### 🔍 Complete Audit Trail")
        st.caption("All actions on this case are immutably logged — regulatory transparency requirement.")
        audit_service.log(
            "CASE_VIEWED", case_id=case.case_id, user_id=user["id"],
            details={"viewed_by": user["username"], "section": "audit_trail"}
        )
        logs = audit_service.get_case_audit_trail(case.case_id)
        if logs:
            for log in logs:
                cat_colors = {
                    "GENERATION": "#1565c0", "EDIT": "#e65100",
                    "APPROVAL": "#2e7d32", "ACCESS": "#607d8b",
                    "AUTH": "#6a1b9a", "ALERT": "#c62828"
                }
                cat = log.action_category or "GENERAL"
                cc = cat_colors.get(cat, "#607d8b")
                with st.expander(
                    f"[{log.created_at.strftime('%d/%m/%Y %H:%M:%S') if log.created_at else ''}] "
                    f"{log.action} — {cat}",
                    expanded=False
                ):
                    i1, i2 = st.columns(2)
                    with i1:
                        st.markdown(f"**Action:** `{log.action}`")
                        st.markdown(f"**Category:** `{cat}`")
                        st.markdown(f"**Status:** {'✅ Success' if log.success else '❌ Failed'}")
                        if log.llm_model_used:
                            st.markdown(f"**LLM Model:** `{log.llm_model_used}`")
                        if log.llm_prompt_hash:
                            st.markdown(f"**Prompt Hash:** `{log.llm_prompt_hash}`")
                    with i2:
                        if log.details:
                            st.markdown("**Details:**")
                            st.json(log.details)
                    if log.reasoning_trace:
                        st.markdown("**AI Reasoning Trace:**")
                        st.markdown(f'<div class="audit-box">{log.reasoning_trace}</div>', unsafe_allow_html=True)
                    if log.data_sources_used:
                        st.markdown("**Data Sources:**")
                        for src in log.data_sources_used:
                            st.markdown(f"- {src}")
                    if log.rules_matched:
                        st.markdown("**Rules/Typologies Matched:**")
                        for rule in log.rules_matched:
                            st.markdown(f"- {rule}")
        else:
            st.info("No audit records found for this case.")

    # ===== VERSIONS TAB =====
    with versions_tab:
        st.markdown("#### 📋 Narrative Version History")
        db_v = SessionLocal()
        try:
            versions = db_v.query(NarrativeVersion)\
                .filter(NarrativeVersion.case_id == case.case_id)\
                .order_by(NarrativeVersion.version_number.desc()).all()
            if versions:
                for v in versions:
                    type_icon = {"GENERATED": "🤖", "EDIT": "✏️", "APPROVED": "✅"}.get(v.change_type, "📝")
                    with st.expander(
                        f"v{v.version_number} | {type_icon} {v.change_type} | "
                        f"{v.created_at.strftime('%d/%m/%Y %H:%M') if v.created_at else ''} | "
                        f"{v.changed_by or 'System'}"
                    ):
                        st.caption(v.change_summary or "No summary")
                        st.markdown(f'<div class="narrative-box" style="max-height:300px;overflow-y:auto;">{v.narrative_text}</div>', unsafe_allow_html=True)
            else:
                st.info("No version history yet.")
        finally:
            db_v.close()
