"""Dashboard Page"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.models.database import SARCase, TransactionAlert, CustomerProfile, CaseStatus, SessionLocal
from app.services.alert_service import alert_service
from app.services.audit_service import audit_service
from app.utils.auth import has_permission
from app.utils.data_processor import ist_now


def get_dashboard_stats():
    db: Session = SessionLocal()
    try:
        total_cases = db.query(SARCase).count()
        open_cases = db.query(SARCase).filter(SARCase.status == CaseStatus.OPEN).count()
        pending_review = db.query(SARCase).filter(SARCase.status == CaseStatus.IN_REVIEW).count()
        approved = db.query(SARCase).filter(SARCase.status == CaseStatus.APPROVED).count()
        filed = db.query(SARCase).filter(SARCase.status == CaseStatus.FILED).count()
        total_alerts = db.query(TransactionAlert).count()
        high_risk_customers = db.query(CustomerProfile).filter(CustomerProfile.risk_rating.in_(["HIGH", "VERY HIGH"])).count()
        return {
            "total_cases": total_cases,
            "open_cases": open_cases,
            "pending_review": pending_review,
            "approved": approved,
            "filed": filed,
            "total_alerts": total_alerts,
            "high_risk_customers": high_risk_customers
        }
    finally:
        db.close()


def get_case_status_df():
    db: Session = SessionLocal()
    try:
        cases = db.query(SARCase).all()
        if not cases:
            return pd.DataFrame()
        data = [{"status": c.status.value, "priority": c.priority, "created_at": c.created_at} for c in cases]
        return pd.DataFrame(data)
    finally:
        db.close()


def get_alert_severity_df():
    db: Session = SessionLocal()
    try:
        alerts = db.query(TransactionAlert).all()
        if not alerts:
            return pd.DataFrame()
        data = [{"severity": a.severity.value, "alert_type": a.alert_type, "total_amount": a.total_amount,
                 "customer_id": a.customer_id, "date": a.created_at} for a in alerts]
        return pd.DataFrame(data)
    finally:
        db.close()


def show_dashboard(user: dict):
    st.markdown(f"""
    <div class="app-header">
        <div>
            <h2 style="margin:0;color:white;">🏦 AML SAR Command Centre</h2>
            <p style="margin:0;opacity:0.8;font-size:0.85rem;">Real-time oversight of Suspicious Activity Reports</p>
        </div>
        <div style="text-align:right;color:rgba(255,255,255,0.7);font-size:0.8rem;">
            {ist_now().strftime('%A, %d %B %Y %H:%M IST')} | {user['full_name']}
        </div>
    </div>
    """, unsafe_allow_html=True)
    stats = get_dashboard_stats()
    alert_summary = alert_service.get_alert_summary()
    audit_stats = audit_service.get_audit_stats()
    # KPI Row 1
    col1, col2, col3, col4, col5 = st.columns(5)
    kpis = [
        (col1, stats["total_cases"], "Total Cases", "#00205b"),
        (col2, stats["open_cases"], "Open Cases", "#e65100"),
        (col3, stats["pending_review"], "Pending Review", "#1565c0"),
        (col4, stats["filed"], "Filed SARs", "#2e7d32"),
        (col5, alert_summary["total"], "Active Alerts", "#c62828"),
    ]
    for col, value, label, color in kpis:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{color};">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("")
    # Charts Row
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.markdown("#### Case Status Distribution")
        df_cases = get_case_status_df()
        if not df_cases.empty:
            status_counts = df_cases["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            colors = {"OPEN": "#e65100", "IN_REVIEW": "#1565c0", "APPROVED": "#2e7d32",
                      "FILED": "#00205b", "CLOSED": "#607d8b", "REJECTED": "#c62828"}
            fig = px.pie(status_counts, values="Count", names="Status",
                        color="Status", color_discrete_map=colors, hole=0.4)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=280,
                              legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No cases yet. Create your first SAR case to see analytics.")
    with col_right:
        st.markdown("#### Alert Severity Breakdown")
        df_alerts = get_alert_severity_df()
        if not df_alerts.empty:
            sev_counts = df_alerts["severity"].value_counts().reset_index()
            sev_counts.columns = ["Severity", "Count"]
            sev_colors = {"CRITICAL": "#c62828", "HIGH": "#e65100", "MEDIUM": "#f9a825", "LOW": "#2e7d32"}
            fig2 = px.bar(sev_counts, x="Severity", y="Count",
                          color="Severity", color_discrete_map=sev_colors,
                          text="Count")
            fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=280,
                               showlegend=False, plot_bgcolor="white",
                               xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0"))
            fig2.update_traces(textposition="outside")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No alerts data available.")
    # Alerts + Activity Row
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("#### 🔔 Recent Alerts")
        recent_alerts = alert_service.get_unread_alerts(limit=5)
        if recent_alerts:
            for a in recent_alerts:
                sev = a.severity.value if hasattr(a.severity, 'value') else a.severity
                css = f"alert-{sev.lower()}"
                st.markdown(f"""
                <div class="{css}">
                    <strong>[{sev}]</strong> {a.title}<br>
                    <small style="opacity:0.7;">{a.message[:100]}...</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No unread alerts")
    with col_b:
        st.markdown("#### 📋 Recent Audit Activity")
        recent_logs = audit_service.get_recent_audit_logs(limit=6)
        if recent_logs:
            for log in recent_logs:
                icon_map = {"GENERATION": "🤖", "EDIT": "✏️", "APPROVAL": "✅",
                            "ACCESS": "👁️", "AUTH": "🔐", "ALERT": "🔔", "SYSTEM": "⚙️"}
                icon = icon_map.get(log.action_category, "📝")
                t = log.created_at.strftime("%d/%m %H:%M") if log.created_at else ""
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0f0;">
                    <span>{icon} <strong>{log.action}</strong> — Case: {log.case_id or 'N/A'}</span>
                    <span style="color:#999;font-size:0.78rem;">{t}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recent activity logged.")
    # Quick Actions
    st.markdown("---")
    st.markdown("#### ⚡ Quick Actions")
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("➕ New SAR Case", use_container_width=True, type="primary"):
            st.session_state["page"] = "generate"
            st.rerun()
    with qa2:
        if st.button("📋 View All Cases", use_container_width=True):
            st.session_state["page"] = "cases"
            st.rerun()
    with qa3:
        if st.button("🔍 Review Queue", use_container_width=True):
            st.session_state["page"] = "review"
            st.rerun()
    with qa4:
        if st.button("📊 Audit Trail", use_container_width=True):
            st.session_state["page"] = "audit"
            st.rerun()
