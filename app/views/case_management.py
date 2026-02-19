"""Case Management Page"""
import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.models.database import SARCase, CustomerProfile, CaseStatus, AlertSeverity, SessionLocal
from app.services.audit_service import audit_service
from app.utils.auth import has_permission


def get_all_cases(user: dict):
    db: Session = SessionLocal()
    try:
        q = db.query(SARCase, CustomerProfile).join(
            CustomerProfile, SARCase.customer_id == CustomerProfile.customer_id, isouter=True
        )
        if not has_permission(user["role"], "view_all_cases"):
            q = q.filter(SARCase.analyst_id == user["id"])
        results = q.order_by(SARCase.created_at.desc()).all()
        rows = []
        for case, customer in results:
            rows.append({
                "Case ID": case.case_id,
                "Customer": customer.full_name if customer else case.customer_id,
                "Customer ID": case.customer_id,
                "Status": case.status.value,
                "Priority": case.priority,
                "Alert ID": case.alert_id or "N/A",
                "Narrative Version": case.narrative_version or 0,
                "Approved By": case.approved_by or "-",
                "SAR Ref": case.sar_reference or "-",
                "Created": case.created_at.strftime("%d/%m/%Y %H:%M") if case.created_at else "-",
                "Updated": case.updated_at.strftime("%d/%m/%Y %H:%M") if case.updated_at else "-",
            })
        return pd.DataFrame(rows)
    finally:
        db.close()


def show_case_management(user: dict):
    st.markdown("""
    <div class="app-header">
        <div>
            <h2 style="margin:0;color:white;">📋 Case Management</h2>
            <p style="margin:0;opacity:0.8;font-size:0.85rem;">Manage and track all SAR cases</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    df = get_all_cases(user)
    if df.empty:
        st.info("No cases found. Generate a SAR to create your first case.")
        if st.button("➕ Generate New SAR", type="primary"):
            st.session_state["page"] = "generate"
            st.rerun()
        return
    # Filters
    f1, f2, f3 = st.columns(3)
    with f1:
        status_filter = st.multiselect(
            "Filter by Status",
            options=["OPEN", "IN_REVIEW", "APPROVED", "FILED", "REJECTED", "CLOSED"],
            default=[]
        )
    with f2:
        priority_filter = st.multiselect("Filter by Priority", options=["LOW", "MEDIUM", "HIGH", "CRITICAL"], default=[])
    with f3:
        search = st.text_input("🔍 Search (Case ID, Customer, Alert...)", "")
    filtered_df = df.copy()
    if status_filter:
        filtered_df = filtered_df[filtered_df["Status"].isin(status_filter)]
    if priority_filter:
        filtered_df = filtered_df[filtered_df["Priority"].isin(priority_filter)]
    if search:
        mask = filtered_df.apply(lambda row: search.lower() in str(row).lower(), axis=1)
        filtered_df = filtered_df[mask]
    # Summary stats
    s1, s2, s3, s4, s5 = st.columns(5)
    status_counts = df["Status"].value_counts()
    for col, status, color in [
        (s1, "OPEN", "#e65100"), (s2, "IN_REVIEW", "#1565c0"),
        (s3, "APPROVED", "#2e7d32"), (s4, "FILED", "#00205b"), (s5, "REJECTED", "#c62828")
    ]:
        with col:
            count = status_counts.get(status, 0)
            col.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{color};">{count}</div>
                <div class="metric-label">{status}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("")
    # Color-code status
    def style_status(val):
        colors = {
            "OPEN": "background:#fff3e0;color:#e65100",
            "IN_REVIEW": "background:#e3f2fd;color:#1565c0",
            "APPROVED": "background:#e8f5e9;color:#2e7d32",
            "FILED": "background:#e8eaf6;color:#283593",
            "REJECTED": "background:#ffebee;color:#c62828",
            "CLOSED": "background:#f5f5f5;color:#607d8b"
        }
        return colors.get(val, "")
    styled = filtered_df.style.applymap(style_status, subset=["Status"])
    st.dataframe(styled, use_container_width=True, height=420)
    st.caption(f"Showing {len(filtered_df)} of {len(df)} cases")
    # Row actions
    st.markdown("---")
    col_sel, col_btn1, col_btn2 = st.columns([2, 1, 1])
    with col_sel:
        if not filtered_df.empty:
            selected_case_id = st.selectbox("Select Case for Action", filtered_df["Case ID"].tolist())
    with col_btn1:
        if st.button("🔍 Review Selected", use_container_width=True, type="primary"):
            st.session_state["review_case_id"] = selected_case_id
            st.session_state["page"] = "review"
            audit_service.log("CASE_VIEWED", case_id=selected_case_id, user_id=user["id"],
                              details={"viewed_by": user["username"]})
            st.rerun()
    with col_btn2:
        if st.button("📊 View Audit Trail", use_container_width=True):
            st.session_state["audit_case_id"] = selected_case_id
            st.session_state["page"] = "audit"
            st.rerun()
    # Export
    if has_permission(user["role"], "export_data") and not df.empty:
        st.markdown("---")
        csv = df.to_csv(index=False)
        st.download_button(
            "⬇️ Export Cases to CSV",
            csv,
            file_name=f"sar_cases_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        audit_service.log("DATA_EXPORTED", user_id=user["id"],
                          details={"exported_by": user["username"], "record_count": len(df)})
