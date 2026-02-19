"""Alerts Page"""
import streamlit as st
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.services.alert_service import alert_service
from app.services.audit_service import audit_service
from app.utils.auth import has_permission


SEV_CSS = {
    "CRITICAL": ("alert-critical", "🔴"),
    "HIGH": ("alert-high", "🟠"),
    "MEDIUM": ("alert-medium", "🟡"),
    "LOW": ("alert-low", "🟢"),
}


def show_alerts(user: dict):
    st.markdown("""
    <div class="app-header">
        <div>
            <h2 style="margin:0;color:white;">🔔 Alerts Centre</h2>
            <p style="margin:0;opacity:0.8;font-size:0.85rem;">Real-time compliance alerts and notifications</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    summary = alert_service.get_alert_summary()
    # Summary row
    s1, s2, s3, s4, s5 = st.columns(5)
    kpi_data = [
        (s1, summary["total"], "Total Unread", "#00205b"),
        (s2, summary["critical"], "Critical", "#c62828"),
        (s3, summary["high"], "High", "#e65100"),
        (s4, summary["medium"], "Medium", "#f9a825"),
        (s5, summary["low"], "Low", "#2e7d32"),
    ]
    for col, val, label, color in kpi_data:
        with col:
            col.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{color};">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("")
    # Controls
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        show_filter = st.selectbox("Filter Severity", ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
    with c2:
        show_unread_only = st.checkbox("Unread Only", value=False)
    with c3:
        if st.button("✅ Mark All as Read", use_container_width=True):
            count = alert_service.mark_all_read()
            audit_service.log("ALERT_ACKNOWLEDGED", user_id=user["id"],
                              details={"acknowledged_by": user["username"], "count": count})
            st.success(f"Marked {count} alerts as read.")
            st.rerun()
    # Load alerts
    severity_filter = None if show_filter == "ALL" else show_filter
    alerts = alert_service.get_all_alerts(limit=200, severity_filter=severity_filter)
    if show_unread_only:
        alerts = [a for a in alerts if not a.is_read]
    if not alerts:
        st.info("✅ No alerts to display.")
        return
    for a in alerts:
        sev = a.severity.value if hasattr(a.severity, 'value') else str(a.severity)
        css, icon = SEV_CSS.get(sev, ("alert-low", "📢"))
        read_badge = "" if not a.is_read else '<span style="color:#bdbdbd;font-size:0.75rem;"> ✓ READ</span>'
        resolved = ""
        if a.resolved_at:
            resolved = f'<span style="color:#2e7d32;font-size:0.75rem;"> ✅ Resolved by {a.resolved_by}</span>'
        with st.container():
            st.markdown(f"""
            <div class="{css}" style="{'opacity:0.65;' if a.is_read else ''}">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <strong>{icon} [{sev}] {a.title}</strong>{read_badge}{resolved}
                    </div>
                    <div style="font-size:0.75rem;color:#888;white-space:nowrap;margin-left:10px;">
                        {a.created_at.strftime('%d/%m/%Y %H:%M') if a.created_at else ''}
                    </div>
                </div>
                <div style="margin-top:4px;font-size:0.84rem;">{a.message}</div>
                <div style="margin-top:4px;font-size:0.77rem;color:#888;">
                    Type: {a.alert_type}
                    {f' | Case: {a.case_id}' if a.case_id else ''}
                    {f' | Customer: {a.customer_id}' if a.customer_id else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
            if not a.is_read:
                col_read, col_resolve, col_goto = st.columns([1, 1, 2])
                with col_read:
                    if st.button("Mark Read", key=f"read_{a.id}"):
                        alert_service.mark_read(a.id)
                        st.rerun()
                with col_resolve:
                    if has_permission(user["role"], "acknowledge_alerts"):
                        if st.button("Resolve", key=f"resolve_{a.id}"):
                            alert_service.resolve_alert(a.id, user["username"])
                            audit_service.log("ALERT_ACKNOWLEDGED", user_id=user["id"],
                                              details={"alert_id": a.id, "resolved_by": user["username"]})
                            st.rerun()
                with col_goto:
                    if a.case_id and st.button(f"Go to Case {a.case_id}", key=f"goto_{a.id}"):
                        st.session_state["review_case_id"] = a.case_id
                        st.session_state["page"] = "review"
                        st.rerun()
