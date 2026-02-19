"""Analytics & Reports Page"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.models.database import (
    SARCase, TransactionAlert, CustomerProfile, AuditLog,
    CaseStatus, SessionLocal
)


def get_analytics_data():
    db: Session = SessionLocal()
    try:
        cases = db.query(SARCase).all()
        alerts = db.query(TransactionAlert).all()
        customers = db.query(CustomerProfile).all()
        audit_logs = db.query(AuditLog).all()
        return cases, alerts, customers, audit_logs
    finally:
        db.close()


def show_analytics(user: dict):
    st.markdown("""
    <div class="app-header">
        <div>
            <h2 style="margin:0;color:white;">📈 Reports & Analytics</h2>
            <p style="margin:0;opacity:0.8;font-size:0.85rem;">
                Compliance performance metrics and trend analysis
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    cases, alerts, customers, audit_logs = get_analytics_data()
    if not cases and not alerts:
        st.info("📊 No data available yet. Generate some SAR cases to see analytics.")
        return
    # KPI row
    total_amount = sum(a.total_amount or 0 for a in alerts)
    avg_tx_per_alert = sum(a.transaction_count or 0 for a in alerts) / max(len(alerts), 1)
    filed_count = sum(1 for c in cases if c.status == CaseStatus.FILED)
    ai_gen_events = sum(1 for l in audit_logs if l.action == "SAR_GENERATION_COMPLETED")
    k1, k2, k3, k4 = st.columns(4)
    for col, val, label, color in [
        (k1, f"₹{total_amount:,.0f}", "Total Alert Value", "#00205b"),
        (k2, f"{avg_tx_per_alert:.1f}", "Avg Tx per Alert", "#1565c0"),
        (k3, filed_count, "SARs Filed", "#2e7d32"),
        (k4, ai_gen_events, "AI Generations", "#e65100"),
    ]:
        with col:
            col.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{color};font-size:1.6rem;">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("")
    # Chart row 1
    cr1, cr2 = st.columns(2)
    with cr1:
        st.markdown("#### SAR Filing Status Distribution")
        if cases:
            status_counts = pd.Series([c.status.value for c in cases]).value_counts()
            status_df = status_counts.reset_index()
            status_df.columns = ["Status", "Count"]
            color_map = {"OPEN": "#e65100", "IN_REVIEW": "#1565c0", "APPROVED": "#2e7d32",
                         "FILED": "#00205b", "REJECTED": "#c62828", "CLOSED": "#607d8b"}
            fig = px.bar(status_df, x="Status", y="Count", color="Status",
                        color_discrete_map=color_map, text="Count")
            fig.update_layout(height=280, showlegend=False, plot_bgcolor="white",
                             xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0"),
                             margin=dict(l=10, r=10, t=10, b=10))
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
    with cr2:
        st.markdown("#### Alert Types by Severity")
        if alerts:
            alert_df = pd.DataFrame([{
                "Type": a.alert_type.replace("_", " "),
                "Severity": a.severity.value if hasattr(a.severity, 'value') else a.severity,
                "Amount": a.total_amount or 0
            } for a in alerts])
            sev_colors = {"CRITICAL": "#c62828", "HIGH": "#e65100", "MEDIUM": "#f9a825", "LOW": "#2e7d32"}
            fig2 = px.scatter(alert_df, x="Type", y="Amount", size="Amount",
                             color="Severity", color_discrete_map=sev_colors,
                             size_max=50)
            fig2.update_layout(height=280, plot_bgcolor="white",
                              xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0"),
                              margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig2, use_container_width=True)
    # Chart row 2
    cr3, cr4 = st.columns(2)
    with cr3:
        st.markdown("#### Customer Risk Rating Breakdown")
        if customers:
            risk_counts = pd.Series([c.risk_rating for c in customers]).value_counts().reset_index()
            risk_counts.columns = ["Risk", "Count"]
            rcolors = {"VERY HIGH": "#c62828", "HIGH": "#e65100", "MEDIUM": "#f9a825", "LOW": "#2e7d32"}
            fig3 = px.pie(risk_counts, values="Count", names="Risk",
                         color="Risk", color_discrete_map=rcolors, hole=0.4)
            fig3.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10),
                              legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig3, use_container_width=True)
    with cr4:
        st.markdown("#### Audit Event Categories")
        if audit_logs:
            cat_counts = pd.Series([l.action_category or "GENERAL" for l in audit_logs]).value_counts().reset_index()
            cat_counts.columns = ["Category", "Count"]
            cat_colors = {
                "GENERATION": "#1565c0", "EDIT": "#e65100", "APPROVAL": "#2e7d32",
                "ACCESS": "#607d8b", "AUTH": "#6a1b9a", "ALERT": "#c62828"
            }
            fig4 = px.bar(cat_counts, x="Category", y="Count", color="Category",
                         color_discrete_map=cat_colors, text="Count")
            fig4.update_layout(height=250, showlegend=False, plot_bgcolor="white",
                              margin=dict(l=10, r=10, t=10, b=10))
            fig4.update_traces(textposition="outside")
            st.plotly_chart(fig4, use_container_width=True)
    # Jurisdiction heatmap
    st.markdown("#### 🌍 Jurisdictions Involved in Alerts")
    if alerts:
        all_jurisdictions = []
        for a in alerts:
            for j in (a.jurisdictions_involved or []):
                all_jurisdictions.append({"Jurisdiction": j, "Alert Type": a.alert_type, "Amount": a.total_amount or 0})
        if all_jurisdictions:
            jdf = pd.DataFrame(all_jurisdictions)
            j_agg = jdf.groupby("Jurisdiction")["Amount"].sum().reset_index()
            j_agg = j_agg.sort_values("Amount", ascending=False)
            fig5 = px.bar(j_agg, x="Jurisdiction", y="Amount",
                         color="Amount", color_continuous_scale="Reds",
                         labels={"Amount": "Total Amount (₹)"})
            fig5.update_layout(height=280, plot_bgcolor="white",
                              xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0"),
                              margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig5, use_container_width=True)
    # Alert score histogram
    if alerts and any(a.alert_score for a in alerts):
        st.markdown("#### 📊 Alert Score Distribution")
        scores = [a.alert_score for a in alerts if a.alert_score]
        fig6 = go.Figure(go.Histogram(x=scores, nbinsx=10,
                                       marker_color="#00205b",
                                       opacity=0.8))
        fig6.update_layout(
            height=220, plot_bgcolor="white", bargap=0.1,
            xaxis=dict(title="Alert Score", gridcolor="#f0f0f0"),
            yaxis=dict(title="Count", gridcolor="#f0f0f0"),
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig6, use_container_width=True)
