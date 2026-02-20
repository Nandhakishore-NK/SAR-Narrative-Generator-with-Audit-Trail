"""Audit Trail Page - Full system-wide audit log viewer"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.services.audit_service import audit_service
from app.models.database import AuditLog, SessionLocal
from app.utils.auth import has_permission
from app.utils.data_processor import to_ist, ist_now


def show_audit_trail(user: dict):
    st.markdown("""
    <div class="app-header">
        <div>
            <h2 style="margin:0;color:white;">📊 Audit Trail</h2>
            <p style="margin:0;opacity:0.8;font-size:0.85rem;">
                Complete immutable audit log — every action, decision and data access recorded
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if not has_permission(user["role"], "view_audit_logs"):
        st.error("🚫 Access Denied: You require SUPERVISOR or ADMIN role to view audit logs.")
        return
    audit_service.log("AUDIT_LOG_VIEWED", user_id=user["id"],
                      details={"viewed_by": user["username"]})
    # Stats
    stats = audit_service.get_audit_stats()
    s1, s2, s3, s4, s5 = st.columns(5)
    kpis = [
        (s1, stats["total_events"], "Total Events", "#00205b"),
        (s2, stats["generation_events"], "AI Generations", "#1565c0"),
        (s3, stats["approval_events"], "Approvals", "#2e7d32"),
        (s4, stats["rejection_events"], "Rejections", "#c62828"),
        (s5, stats["edit_events"], "Edits", "#e65100"),
    ]
    for col, val, label, color in kpis:
        with col:
            col.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{color};">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("")
    # Filters
    f1, f2, f3 = st.columns(3)
    with f1:
        pre_case = st.session_state.pop("audit_case_id", None)
        case_filter = st.text_input("Filter by Case ID", value=pre_case or "", placeholder="e.g. SAR-202401-ABC123")
    with f2:
        cat_filter = st.selectbox(
            "Filter by Category",
            ["ALL", "GENERATION", "EDIT", "APPROVAL", "ACCESS", "AUTH", "ALERT", "SYSTEM"]
        )
    with f3:
        limit = st.slider("Records to display", 20, 500, 100, step=20)
    # Load logs
    db: SessionLocal = SessionLocal()
    try:
        q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
        if case_filter:
            q = q.filter(AuditLog.case_id == case_filter)
        if cat_filter != "ALL":
            q = q.filter(AuditLog.action_category == cat_filter)
        logs = q.limit(limit).all()
    finally:
        db.close()
    if not logs:
        st.info("No audit records found matching your filters.")
        return
    # Table view
    rows = []
    for log in logs:
        rows.append({
            "Timestamp": to_ist(log.created_at).strftime("%d/%m/%Y %H:%M:%S IST") if log.created_at else "-",
            "Action": log.action,
            "Category": log.action_category or "-",
            "Case ID": log.case_id or "-",
            "User ID": log.user_id or "-",
            "Model": log.llm_model_used or "-",
            "Prompt Hash": log.llm_prompt_hash or "-",
            "Success": "✅" if log.success else "❌",
        })
    df = pd.DataFrame(rows)
    def style_category(val):
        cat_colors = {
            "GENERATION": "background:#e3f2fd;color:#1565c0",
            "EDIT": "background:#fff3e0;color:#e65100",
            "APPROVAL": "background:#e8f5e9;color:#2e7d32",
            "AUTH": "background:#f3e5f5;color:#6a1b9a",
            "ALERT": "background:#ffebee;color:#c62828",
            "ACCESS": "background:#f5f5f5;color:#455a64",
        }
        return cat_colors.get(val, "")
    styled = df.style.applymap(style_category, subset=["Category"])
    st.dataframe(styled, use_container_width=True, height=350)
    st.caption(f"Showing {len(logs)} records")
    # Detailed view
    st.markdown("---")
    st.markdown("#### 🔍 Detailed Log Inspector")
    for log in logs[:20]:
        cat_icons = {
            "GENERATION": "🤖", "EDIT": "✏️", "APPROVAL": "✅",
            "ACCESS": "👁️", "AUTH": "🔐", "ALERT": "🔔", "SYSTEM": "⚙️"
        }
        icon = cat_icons.get(log.action_category, "📝")
        with st.expander(
            f"{icon} [{to_ist(log.created_at).strftime('%d/%m/%Y %H:%M:%S IST') if log.created_at else ''}] "
            f"{log.action} | Case: {log.case_id or 'N/A'}",
            expanded=False
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Action:** `{log.action}`")
                st.markdown(f"**Category:** `{log.action_category}`")
                st.markdown(f"**Case ID:** `{log.case_id or 'N/A'}`")
                st.markdown(f"**User ID:** `{log.user_id or 'System'}`")
                st.markdown(f"**Result:** {'✅ Success' if log.success else f'❌ Failed: {log.error_message}'}")
            with c2:
                if log.llm_model_used:
                    st.markdown(f"**LLM Model:** `{log.llm_model_used}`")
                if log.llm_prompt_hash:
                    st.markdown(f"**Prompt Hash:** `{log.llm_prompt_hash}`")
                if log.details:
                    st.markdown("**Event Details:**")
                    st.json(log.details)
            if log.reasoning_trace:
                st.markdown("**AI Reasoning Trace:**")
                st.markdown(f'<div class="audit-box">{log.reasoning_trace}</div>', unsafe_allow_html=True)
            if log.data_sources_used:
                st.markdown(f"**Data Sources:** {', '.join(log.data_sources_used)}")
            if log.rules_matched:
                st.markdown(f"**Rules Matched:** {', '.join(log.rules_matched)}")
    # Export
    if has_permission(user["role"], "export_data"):
        st.markdown("---")
        csv = pd.DataFrame(rows).to_csv(index=False)
        st.download_button(
            "⬇️ Export Audit Log to CSV",
            csv,
            file_name=f"audit_log_export_{ist_now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
