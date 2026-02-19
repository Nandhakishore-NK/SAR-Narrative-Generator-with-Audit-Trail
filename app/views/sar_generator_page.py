"""SAR Generator Page - Core narrative generation interface"""
import streamlit as st
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.models.database import (
    CustomerProfile, TransactionAlert, SARCase, NarrativeVersion,
    CaseStatus, SessionLocal
)
from app.services.sar_generator import sar_generator
from app.services.audit_service import audit_service
from app.services.alert_service import alert_service
from app.utils.data_processor import get_customer_dict, get_alert_dict
from app.utils.auth import has_permission


def load_customers():
    db: Session = SessionLocal()
    try:
        return db.query(CustomerProfile).all()
    finally:
        db.close()


def load_alerts(customer_id: str = None):
    db: Session = SessionLocal()
    try:
        q = db.query(TransactionAlert)
        if customer_id:
            q = q.filter(TransactionAlert.customer_id == customer_id)
        return q.all()
    finally:
        db.close()


def save_case(
    customer_id: str, alert_id: str, generated_narrative: str,
    generation_result, analyst_id: int, hosting_env: str
) -> str:
    db: Session = SessionLocal()
    try:
        case_id = f"SAR-{datetime.now().strftime('%Y%m')}-{str(uuid.uuid4().hex[:6]).upper()}"
        case = SARCase(
            case_id=case_id,
            alert_id=alert_id,
            customer_id=customer_id,
            analyst_id=analyst_id,
            status=CaseStatus.IN_REVIEW,
            generated_narrative=generated_narrative,
            narrative_version=1,
            generation_metadata={
                "model": generation_result.model_used,
                "generation_time": generation_result.generation_time_seconds,
                "tokens_used": generation_result.tokens_used,
                "confidence_level": generation_result.confidence_level,
                "hosting_environment": hosting_env,
                "generated_at": datetime.utcnow().isoformat()
            },
            rag_sources_used=generation_result.rag_sources,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(case)
        version = NarrativeVersion(
            case_id=case_id,
            version_number=1,
            narrative_text=generated_narrative,
            change_type="GENERATED",
            change_summary="Initial AI-generated narrative",
            created_at=datetime.utcnow()
        )
        db.add(version)
        db.commit()
        return case_id
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def show_sar_generator(user: dict):
    st.markdown("""
    <div class="app-header">
        <div>
            <h2 style="margin:0;color:white;">✍️ SAR Narrative Generator</h2>
            <p style="margin:0;opacity:0.8;font-size:0.85rem;">
                AI-powered narrative generation with full audit trail
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if not has_permission(user["role"], "generate_sar"):
        st.error("🚫 Access Denied: You do not have permission to generate SAR narratives.")
        return

    tab1, tab2 = st.tabs(["🤖 Generate from Alert", "📝 Manual Entry"])

    # ==================== TAB 1: FROM ALERT ====================
    with tab1:
        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.markdown("#### 1️⃣ Select Customer & Alert")
            customers = load_customers()
            if not customers:
                st.warning("No customers found. Sample data may not be loaded.")
                return
            customer_options = {f"{c.full_name} ({c.customer_id}) [{c.risk_rating}]": c for c in customers}
            selected_customer_label = st.selectbox("Customer", list(customer_options.keys()))
            selected_customer = customer_options[selected_customer_label]
            alerts = load_alerts(selected_customer.customer_id)
            if alerts:
                alert_options = {
                    f"[{a.severity.value}] {a.alert_type} | ₹{a.total_amount:,.0f} | {a.alert_id}": a
                    for a in alerts
                }
                selected_alert_label = st.selectbox("Transaction Alert", list(alert_options.keys()))
                selected_alert = alert_options[selected_alert_label]
                # Customer profile preview
                st.markdown("##### Customer Profile")
                c = selected_customer
                risk_col = {"HIGH": "#e65100", "VERY HIGH": "#c62828", "MEDIUM": "#f9a825", "LOW": "#2e7d32"}
                rc = risk_col.get(c.risk_rating, "#607d8b")
                st.markdown(f"""
                <div style="background:#f8f9fc;padding:12px;border-radius:8px;border:1px solid #e0e0e0;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <b>{c.full_name}</b>
                        <span style="background:{rc};color:white;padding:2px 8px;border-radius:10px;font-size:0.75rem;">{c.risk_rating}</span>
                    </div>
                    <div style="font-size:0.83rem;color:#555;margin-top:6px;">
                        <div>🏢 {c.occupation} @ {c.employer or 'N/A'}</div>
                        <div>� Annual Income: ₹{c.annual_income:,.0f}</div>
                        <div>🌍 Nationality: {c.nationality}</div>
                        <div>{'⚠️ PEP Customer' if c.pep_status else '✅ Non-PEP'} | KYC: {c.kyc_status}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No alerts for this customer.")
                return
        with col_right:
            if alerts:
                st.markdown("#### 2️⃣ Alert Details")
                a = selected_alert
                sev_col = {"CRITICAL": "#c62828", "HIGH": "#e65100", "MEDIUM": "#f9a825", "LOW": "#2e7d32"}
                sc = sev_col.get(a.severity.value if hasattr(a.severity, 'value') else a.severity, "#607d8b")
                sev_val = a.severity.value if hasattr(a.severity, 'value') else a.severity
                st.markdown(f"""
                <div style="background:#fff8f0;padding:12px;border-radius:8px;border-left:4px solid {sc};margin-bottom:10px;">
                    <div style="display:flex;justify-content:space-between;">
                        <b>{a.alert_type.replace('_', ' ')}</b>
                        <span style="background:{sc};color:white;padding:2px 8px;border-radius:10px;font-size:0.75rem;">{sev_val}</span>
                    </div>
                    <div style="margin-top:6px;font-size:0.83rem;color:#555;">
                        <div>💰 Total: <b>₹{a.total_amount:,.2f}</b> across {a.transaction_count} transactions</div>
                        <div>📅 {a.date_range_start} → {a.date_range_end}</div>
                        <div>🌍 Jurisdictions: {', '.join(a.jurisdictions_involved or ['UK'])}</div>
                        <div>📊 Alert Score: <b>{a.alert_score}/100</b></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("**Triggering Factors:**")
                for factor in (a.triggering_factors or []):
                    st.markdown(f"- {factor}")
                st.markdown("#### 3️⃣ Generation Settings")
                hosting_env = st.selectbox(
                    "Hosting Environment",
                    ["on-premises", "cloud-aws", "cloud-azure", "multi-cloud"],
                    help="System will tailor compliance considerations to your hosting environment"
                )
                include_rag = st.checkbox("Use RAG (SAR templates + regulatory context)", value=True)
                st.caption("RAG retrieves relevant SAR templates and JMLSG/POCA regulatory guidance from ChromaDB")

        if alerts:
            st.markdown("---")
            gen_col1, gen_col2, gen_col3 = st.columns([1, 2, 1])
            with gen_col2:
                generate_btn = st.button(
                    "🤖 Generate SAR Narrative with AI",
                    use_container_width=True,
                    type="primary",
                    help="Generate a complete SAR narrative using LLM + RAG pipeline"
                )
            if generate_btn:
                with st.spinner("🔄 Generating SAR narrative... Retrieving regulatory context, analysing data, drafting narrative..."):
                    try:
                        customer_dict = get_customer_dict(selected_customer)
                        alert_dict = get_alert_dict(selected_alert)
                        transaction_data = selected_alert.transaction_data or []
                        audit_service.log(
                            action="SAR_GENERATION_STARTED",
                            user_id=user["id"],
                            details={
                                "customer_id": selected_customer.customer_id,
                                "alert_id": selected_alert.alert_id,
                                "hosting_environment": hosting_env
                            }
                        )
                        result = sar_generator.generate_narrative(
                            customer_data=customer_dict,
                            alert_data=alert_dict,
                            transaction_data=transaction_data,
                            hosting_environment=hosting_env
                        )
                        case_id = save_case(
                            customer_id=selected_customer.customer_id,
                            alert_id=selected_alert.alert_id,
                            generated_narrative=result.narrative,
                            generation_result=result,
                            analyst_id=user["id"],
                            hosting_env=hosting_env
                        )
                        audit_service.log_generation(case_id, user["id"], result, hosting_env)
                        alert_service.create_alert(
                            alert_type="NARRATIVE_GENERATED",
                            message=f"SAR narrative generated for case {case_id}. Customer: {selected_customer.full_name}. Confidence: {result.confidence_level}",
                            case_id=case_id,
                            customer_id=selected_customer.customer_id
                        )
                        st.session_state["last_generated"] = {
                            "case_id": case_id,
                            "result": result,
                            "customer": customer_dict,
                            "alert": alert_dict
                        }
                        st.success(f"✅ SAR Narrative generated! Case ID: **{case_id}**")
                    except Exception as e:
                        audit_service.log(
                            action="SAR_GENERATION_FAILED",
                            user_id=user["id"],
                            success=False,
                            error_message=str(e)
                        )
                        st.error(f"Generation failed: {e}")
            # Show last generated result
            if "last_generated" in st.session_state:
                gen_data = st.session_state["last_generated"]
                result = gen_data["result"]
                st.markdown("---")
                st.markdown(f"### 📄 Case {gen_data['case_id']} — Generated Narrative")
                # Metadata strip
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Confidence", result.confidence_level)
                with m2:
                    st.metric("Model", result.model_used.split(":")[-1] if ":" in result.model_used else result.model_used)
                with m3:
                    st.metric("Gen Time", f"{result.generation_time_seconds:.1f}s")
                with m4:
                    st.metric("Tokens", str(result.tokens_used or "N/A"))
                nar_tab, audit_tab, rag_tab = st.tabs(["📄 Narrative", "🔍 Audit Trail", "📚 RAG Sources"])
                with nar_tab:
                    st.markdown(f'<div class="narrative-box">{result.narrative}</div>', unsafe_allow_html=True)
                    dl_col1, dl_col2 = st.columns(2)
                    with dl_col1:
                        st.download_button(
                            "⬇️ Download Narrative (.txt)",
                            result.narrative,
                            file_name=f"{gen_data['case_id']}_narrative.txt",
                            mime="text/plain"
                        )
                    with dl_col2:
                        if st.button("✅ Go to Review & Approve", type="primary"):
                            st.session_state["page"] = "review"
                            st.session_state["review_case_id"] = gen_data["case_id"]
                            st.rerun()
                with audit_tab:
                    st.markdown("#### 🔍 AI Reasoning Trace")
                    audit_data = result.audit_trail
                    a1, a2 = st.columns(2)
                    with a1:
                        st.markdown("**Risk Indicators Extracted:**")
                        for indicator in audit_data.get("risk_indicators_extracted", []):
                            st.markdown(f"⚠️ {indicator}")
                        st.markdown("**Typologies Matched:**")
                        for typo in audit_data.get("typologies_matched", ["Extracting..."]):
                            st.markdown(f"🎯 {typo}")
                    with a2:
                        st.markdown("**Data Sources Used:**")
                        for src in audit_data.get("data_sources_used", ["Customer KYC", "Transaction Alert"]):
                            st.markdown(f"📌 {src}")
                        st.markdown("**Prompt Hash:**")
                        st.code(audit_data.get("prompt_hash", "N/A"))
                    st.markdown("**Full Reasoning Trace:**")
                    from app.services.audit_service import audit_service as _audit
                    logs = _audit.get_case_audit_trail(gen_data["case_id"])
                    for log in logs:
                        if log.reasoning_trace:
                            st.markdown(f'<div class="audit-box">{log.reasoning_trace}</div>', unsafe_allow_html=True)
                with rag_tab:
                    st.markdown("#### 📚 Retrieved Context from ChromaDB")
                    templates = result.rag_sources.get("templates", [])
                    regulations = result.rag_sources.get("regulations", [])
                    st.markdown(f"**Templates Retrieved:** {len(templates)}")
                    for t in templates:
                        with st.expander(f"📋 {t['metadata'].get('title', t['id'])}"):
                            st.text(t["content"][:600] + "...")
                    st.markdown(f"**Regulations Retrieved:** {len(regulations)}")
                    for r in regulations:
                        with st.expander(f"⚖️ {r['metadata'].get('title', r['id'])}"):
                            st.text(r["content"][:600] + "...")

    # ==================== TAB 2: MANUAL ====================
    with tab2:
        st.markdown("#### Manual Case Entry")
        st.info("Manually enter customer and transaction data to generate a SAR narrative.")
        with st.form("manual_entry_form"):
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown("**Customer Information**")
                manual_name = st.text_input("Full Name*", placeholder="e.g. John Smith")
                manual_cid = st.text_input("Customer ID*", value=f"CUST-MANUAL-{str(uuid.uuid4().hex[:4]).upper()}")
                manual_occ = st.text_input("Occupation", placeholder="e.g. Business Owner")
                manual_income = st.number_input("Annual Income (₹)", min_value=0.0, value=50000.0, step=1000.0)
                manual_nationality = st.text_input("Nationality", placeholder="e.g. British")
                manual_risk = st.selectbox("Risk Rating", ["LOW", "MEDIUM", "HIGH", "VERY HIGH"], index=2)
                manual_pep = st.checkbox("PEP Customer")
            with mc2:
                st.markdown("**Alert / Transaction Information**")
                manual_alert_type = st.selectbox("Alert Type", [
                    "STRUCTURING", "RAPID_MOVEMENT", "HIGH_RISK_JURISDICTION",
                    "MULE_ACCOUNT", "TRADE_BASED_ML", "ROUND_TRIP", "OTHER"
                ])
                manual_total = st.number_input("Total Transaction Amount (₹)", min_value=0.0, value=100000.0, step=1000.0)
                manual_tx_count = st.number_input("Number of Transactions", min_value=1, value=10)
                manual_jurisdictions = st.text_input("Jurisdictions Involved", placeholder="e.g. UK, UAE, Cayman Islands")
                manual_counterparties = st.text_area("Counterparties (one per line)", height=60)
                manual_factors = st.text_area("Triggering Factors / Suspicious Indicators (one per line)", height=80)
                manual_env = st.selectbox("Hosting Environment", ["on-premises", "cloud-aws", "cloud-azure", "multi-cloud"])
            submitted_manual = st.form_submit_button("🤖 Generate SAR Narrative", type="primary", use_container_width=True)

        if submitted_manual:
            if not manual_name or not manual_cid:
                st.error("Customer Name and ID are required.")
            else:
                with st.spinner("Generating SAR narrative..."):
                    try:
                        customer_dict = {
                            "customer_id": manual_cid,
                            "full_name": manual_name,
                            "occupation": manual_occ,
                            "annual_income": manual_income,
                            "nationality": manual_nationality,
                            "risk_rating": manual_risk,
                            "pep_status": manual_pep,
                            "kyc_status": "VERIFIED"
                        }
                        alert_dict = {
                            "alert_id": f"ALT-MANUAL-{str(uuid.uuid4().hex[:6]).upper()}",
                            "alert_type": manual_alert_type,
                            "total_amount": manual_total,
                            "transaction_count": int(manual_tx_count),
                            "jurisdictions_involved": [j.strip() for j in manual_jurisdictions.split(",") if j.strip()],
                            "counterparties": [c.strip() for c in manual_counterparties.split("\n") if c.strip()],
                            "triggering_factors": [f.strip() for f in manual_factors.split("\n") if f.strip()],
                            "severity": "HIGH"
                        }
                        result = sar_generator.generate_narrative(
                            customer_data=customer_dict,
                            alert_data=alert_dict,
                            transaction_data=[],
                            hosting_environment=manual_env
                        )
                        st.success("✅ Narrative generated!")
                        st.markdown(f'<div class="narrative-box">{result.narrative}</div>', unsafe_allow_html=True)
                        st.download_button(
                            "⬇️ Download Narrative (.txt)", result.narrative,
                            file_name="manual_sar_narrative.txt", mime="text/plain"
                        )
                        with st.expander("🔍 AI Reasoning Trace"):
                            st.json(result.audit_trail)
                    except Exception as e:
                        st.error(f"Generation error: {e}")
