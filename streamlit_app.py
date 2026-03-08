"""
STR / SAR Narrative Generator with Audit Trail
India AML Compliance Platform — PMLA 2002 / FIU-IND
=========================================
Multi-page Streamlit app: login, role-based sidebar navigation, dashboard,
case management, STR/SAR generation, review & approve, alerts centre, audit trail,
reports & analytics, and user management.
"""

import hashlib
import html
import json
import re
import uuid
from datetime import datetime, timezone, timedelta

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page config (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SAR Guardian – India AML | PMLA 2002",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Login card */
.login-card {
    background: linear-gradient(135deg, #0a1628 0%, #1a2a4a 100%);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 40px;
    max-width: 420px;
    margin: 60px auto;
    text-align: center;
}
.login-title { font-size: 1.6rem; font-weight: 700; color: #e8eaf6; margin-bottom: 4px; }
.login-sub   { font-size: 0.9rem; color: #90caf9; margin-bottom: 24px; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a1628 0%, #0d2244 60%, #0a1628 100%);
    border-right: 1px solid #1e3a5f;
}
.sidebar-logo  { font-size: 1.3rem; font-weight: 800; color: #1e88e5; letter-spacing: 1px; }
.sidebar-user  { font-size: 0.9rem; color: #cdd5e0; }
.role-badge    { display:inline-block; padding:2px 10px; border-radius:12px;
                 font-size:0.7rem; font-weight:700; letter-spacing:1px; }
.role-ADMIN      { background:#1565c0; color:white; }
.role-SUPERVISOR { background:#6a1b9a; color:white; }
.role-ANALYST    { background:#00695c; color:white; }
.role-READ_ONLY  { background:#37474f; color:white; }

/* Alerts */
.alert-card {
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 12px;
    border-left: 5px solid;
    position: relative;
}
.alert-CRITICAL { background: rgba(183,28,28,0.15); border-color: #b71c1c; }
.alert-HIGH     { background: rgba(229,57,53,0.12); border-color: #e53935; }
.alert-MEDIUM   { background: rgba(251,140,0,0.12); border-color: #fb8c00; }
.alert-LOW      { background: rgba(56,142,60,0.12); border-color: #388e3c; }
.unread-dot     { display:inline-block; width:8px; height:8px; background:#1e88e5;
                  border-radius:50%; margin-right:8px; vertical-align:middle; }

/* Severity badges */
.sev-CRITICAL { background:#b71c1c; color:white; padding:3px 10px; border-radius:6px; font-weight:700; font-size:0.8rem; }
.sev-HIGH     { background:#e53935; color:white; padding:3px 10px; border-radius:6px; font-weight:700; font-size:0.8rem; }
.sev-MEDIUM   { background:#fb8c00; color:white; padding:3px 10px; border-radius:6px; font-weight:700; font-size:0.8rem; }
.sev-LOW      { background:#388e3c; color:white; padding:3px 10px; border-radius:6px; font-weight:700; font-size:0.8rem; }

/* Misc */
.section-header {
    font-size: 1.05rem; font-weight: 600; color: #e8eaf6;
    background: #1565c0; padding: 6px 14px; border-radius: 6px; margin-bottom: 10px;
}
.hash-box { font-family:monospace; font-size:0.75rem; color:#90caf9;
            background:#0d1117; padding:4px 8px; border-radius:4px; }
.metric-card {
    background: linear-gradient(135deg, #0a1628, #1a2a4a);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 18px;
    text-align: center;
}
.metric-val   { font-size: 2rem; font-weight: 800; color: #1e88e5; }
.metric-label { font-size: 0.8rem; color: #90caf9; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Demo user database
# ─────────────────────────────────────────────────────────────────────────────
USERS = {
    "admin": {
        "password": "Admin@2024!",
        "name": "System Administrator",
        "role": "ADMIN",
        "department": "IT Security",
        "active": True,
    },
    "analyst1": {
        "password": "Analyst@2024!",
        "name": "Priya Sharma",
        "role": "ANALYST",
        "department": "AML Compliance",
        "active": True,
    },
    "supervisor1": {
        "password": "Supervisor@2024!",
        "name": "Vikram Nair",
        "role": "SUPERVISOR",
        "department": "AML Compliance",
        "active": True,
    },
    "readonly1": {
        "password": "Readonly@2024!",
        "name": "Ananya Krishnamurthy",
        "role": "READ_ONLY",
        "department": "Internal Audit",
        "active": True,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Sample data generators
# ─────────────────────────────────────────────────────────────────────────────
def _sample_cases():
    return [
        {"case_id": "CASE-001", "customer_name": "Rajesh Kumar", "risk_rating": "HIGH",
         "status": "IN_REVIEW", "alert_type": "Structuring", "created_at": "2024-01-15"},
        {"case_id": "CASE-002", "customer_name": "Offshore Holdings Pvt Ltd", "risk_rating": "CRITICAL",
         "status": "SUBMITTED", "alert_type": "Layering", "created_at": "2024-01-18"},
        {"case_id": "CASE-003", "customer_name": "Kavitha Reddy", "risk_rating": "MEDIUM",
         "status": "DRAFT", "alert_type": "Velocity Spike", "created_at": "2024-01-20"},
        {"case_id": "CASE-004", "customer_name": "TechCorp Solutions Pvt Ltd", "risk_rating": "HIGH",
         "status": "APPROVED", "alert_type": "PEP Risk", "created_at": "2024-01-22"},
        {"case_id": "CASE-005", "customer_name": "Deepak Patel", "risk_rating": "CRITICAL",
         "status": "IN_REVIEW", "alert_type": "Smurfing", "created_at": "2024-01-25"},
    ]

def _sample_alerts():
    return [
        {"id": "ALT-001", "severity": "CRITICAL", "title": "Smurfing Pattern Detected",
         "message": "Customer CUST-0891 shows 47 sub-threshold NEFT deposits in 72 hours totalling ₹48 L (below ₹10L CTR threshold).",
         "time": "2 min ago", "read": False, "case_id": "CASE-005"},
        {"id": "ALT-002", "severity": "HIGH", "title": "Offshore Wire Transfer Alert",
         "message": "Multiple SWIFT transfers to UAE counterparty flagged under PMLA Section 12. Total: ₹19.2 Cr.",
         "time": "15 min ago", "read": False, "case_id": "CASE-002"},
        {"id": "ALT-003", "severity": "HIGH", "title": "PEP Transaction Flagged",
         "message": "Politically Exposed Person transaction ₹15 L — Enhanced Due Diligence required per RBI KYC Master Circular.",
         "time": "1 hr ago", "read": False, "case_id": "CASE-004"},
        {"id": "ALT-004", "severity": "MEDIUM", "title": "Velocity Threshold Breach",
         "message": "RTGS/NEFT transaction velocity 3.2x above 90-day average for CUST-0234 — FIU-IND velocity rule triggered.",
         "time": "3 hr ago", "read": True, "case_id": "CASE-003"},
        {"id": "ALT-005", "severity": "MEDIUM", "title": "Round-Number Cash Transactions",
         "message": "6 consecutive round-number cash withdrawals detected — possible smurfing below ₹50,000 threshold.",
         "time": "5 hr ago", "read": True, "case_id": "CASE-001"},
        {"id": "ALT-006", "severity": "LOW", "title": "KYC Address Mismatch",
         "message": "Aadhaar/PAN address does not match transaction origination location — CKYC re-verification required.",
         "time": "1 day ago", "read": True, "case_id": "CASE-003"},
    ]

def _sample_audit_log():
    return [
        {"timestamp": "2024-01-25 09:14:32", "user": "analyst1", "action": "STR_GENERATED",
         "case_id": "CASE-005", "details": "AI narrative generated for smurfing case (PMLA STR)"},
        {"timestamp": "2024-01-25 09:30:11", "user": "supervisor1", "action": "STR_REVIEWED",
         "case_id": "CASE-005", "details": "Narrative reviewed and approved for FIU-IND submission"},
        {"timestamp": "2024-01-24 14:22:05", "user": "analyst1", "action": "CASE_CREATED",
         "case_id": "CASE-005", "details": "New suspicious activity case created under PMLA 2002"},
        {"timestamp": "2024-01-23 11:05:47", "user": "admin", "action": "USER_LOGIN",
         "case_id": "—", "details": "Admin login from 10.0.0.5"},
        {"timestamp": "2024-01-22 16:45:33", "user": "analyst1", "action": "STR_GENERATED",
         "case_id": "CASE-004", "details": "PEP risk STR narrative generated per RBI KYC Master Circular"},
    ]

# ─────────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────────────────────
_defaults = {
    "authenticated": False,
    "username": None,
    "current_page": "Dashboard",
    "transactions": [],
    "rule_triggers": [],
    "sar_history": [],
    "current_sar": None,
    "generation_error": None,
    "cases": _sample_cases(),
    "alerts": _sample_alerts(),
    "audit_log": _sample_audit_log(),
    "users": {k: dict(v) for k, v in USERS.items()},
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def format_inr(amount: float) -> str:
    """Format amount using Indian number system (lakhs / crores)."""
    if amount >= 1_00_00_000:
        return f"₹{amount / 1_00_00_000:.2f} Cr"
    elif amount >= 1_00_000:
        return f"₹{amount / 1_00_000:.2f} L"
    elif amount >= 1000:
        return f"₹{amount:,.0f}"
    else:
        return f"₹{amount:.2f}"

def unread_count() -> int:
    return sum(1 for a in st.session_state.alerts if not a["read"])

def current_user() -> dict:
    return st.session_state.users.get(st.session_state.username, {})

def role() -> str:
    return current_user().get("role", "READ_ONLY")

def can_generate() -> bool:
    return role() in ("ADMIN", "ANALYST")

def can_approve() -> bool:
    return role() in ("ADMIN", "SUPERVISOR")

def _get_llm_client(api_key: str, provider: str):
    try:
        if provider == "Groq":
            from langchain_groq import ChatGroq
            return ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2,
                            groq_api_key=api_key, max_tokens=4096)
        else:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o", temperature=0.2,
                              openai_api_key=api_key, max_tokens=4096)
    except Exception:
        return None

SYSTEM_PROMPT = """You are a Regulator-Grade Financial Crime Compliance AI Engine specialised for the Indian AML/CFT framework.
Generate STR (Suspicious Transaction Report) draft narratives and complete machine-auditable reasoning records compliant with:
- PMLA 2002 (Prevention of Money Laundering Act) and 2023 Amendments
- FIU-IND reporting obligations: STR, CTR (≥₹10L cash), NTR, CCR — filed under PMLA Section 12
- RBI Master Direction on Know Your Customer (KYC) 2016 (updated 2023)
- SEBI AML/CFT Guidelines for regulated entities
- FATF Recommendations (India — FATF Member; mutual evaluation framework)

Indian Regulatory Thresholds:
- CTR: Cash transactions ≥ ₹10,00,000 (₹10 lakhs) in a single day
- STR: All suspicious transactions regardless of amount — due within 7 working days of suspicion
- NTR: Cash transactions ≥ ₹50,000 by non-customers
- Structuring threshold: Transactions structured to avoid ₹50,000 or ₹10L reporting limits

RULES:
- Use ONLY the structured case data provided. Do NOT fabricate data.
- Use regulator-safe language. Do NOT assert criminal guilt.
- Base suspicion solely on observed financial behaviour patterns.
- Reference applicable PMLA sections and FIU-IND/RBI guidelines where relevant.
- Use Indian number system: lakhs (L) and crores (Cr) for amounts, not millions/billions.

OUTPUT TWO SECTIONS EXACTLY:

SECTION A — STR DRAFT NARRATIVE (FIU-IND Format)
## 1. Subject Information
## 2. Summary of Suspicious Activity
## 3. Detailed Transaction Pattern Analysis
## 4. Typology Mapping (FATF / FIU-IND Typology)
## 5. Risk Scoring & Threshold Analysis (PMLA/RBI Thresholds)
## 6. Regulatory Obligations & Reporting Basis
## 7. Data Completeness & Limitations
## 8. Conclusion & Recommended Next Steps

SECTION B — COMPLETE AUDIT TRAIL (STRICT JSON, no markdown fences):
{
  "case_id": "<case_id>",
  "regulatory_framework": "PMLA 2002 | FIU-IND | RBI KYC Master Direction | FATF",
  "reporting_obligation": "STR to FIU-IND under PMLA Section 12",
  "model_metadata": {"model_version": "llama-3.3-70b-versatile", "generation_timestamp": "<ISO-8601>"},
  "data_sources_used": [],
  "triggering_rules": [],
  "thresholds_breached": [],
  "typology_matches": [],
  "transaction_ids_referenced": [],
  "risk_scores_used": {},
  "data_completeness_metrics": {},
  "reasoning_trace": [
    {"sentence_id": "S001", "narrative_sentence": "exact sentence",
     "supporting_transaction_ids": [], "rule_reference": "", "confidence_level": "LOW|MEDIUM|HIGH"}
  ],
  "alert_metadata": {
    "alert_severity": "LOW|MEDIUM|HIGH|CRITICAL",
    "escalation_required": true,
    "recommended_next_steps": []
  },
  "identified_data_gaps": [],
  "model_limitations": "LLM-generated STR narrative requires review by a qualified PMLA Compliance Officer before submission to FIU-IND.",
  "governance_flags": []
}"""

def _build_case_prompt(case, transactions, rule_triggers):
    return (f"CASE DATA:\n{json.dumps(case, indent=2, default=str)}\n\n"
            f"TRANSACTIONS ({len(transactions)} records):\n{json.dumps(transactions, indent=2, default=str)}\n\n"
            f"RULE TRIGGERS ({len(rule_triggers)} records):\n{json.dumps(rule_triggers, indent=2, default=str)}\n\n"
            f"Generate the SAR narrative and audit trail now.")

def _parse_sar_output(raw: str, case_id: str) -> dict:
    section_b_match = re.search(r"SECTION B.*?AUDIT TRAIL.*?\n([\s\S]*)", raw, re.IGNORECASE)
    audit_json, narrative = {}, raw
    if section_b_match:
        raw_json_str = section_b_match.group(1).strip()
        raw_json_str = re.sub(r"```[a-z]*", "", raw_json_str).strip().rstrip("`").strip()
        start, end = raw_json_str.find("{"), raw_json_str.rfind("}") + 1
        if start != -1 and end > start:
            try:
                audit_json = json.loads(raw_json_str[start:end])
            except json.JSONDecodeError:
                audit_json = {"parse_error": "Could not decode audit JSON", "raw": raw_json_str[start:end][:500]}
        sec_b_start = raw.upper().find("SECTION B")
        if sec_b_start != -1:
            narrative = raw[:sec_b_start].strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narrative) if len(s.strip()) > 20]
    return {
        "case_id": case_id,
        "narrative": narrative,
        "audit": audit_json,
        "sentences_with_hashes": [{"sentence": s, "hash": sha256(s)} for s in sentences],
        "severity": audit_json.get("alert_metadata", {}).get("alert_severity", "UNKNOWN"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

def generate_sar(case, transactions, rule_triggers, api_key, provider):
    from langchain_core.messages import SystemMessage, HumanMessage
    llm = _get_llm_client(api_key, provider)
    if llm is None:
        raise RuntimeError("Could not initialise LLM client — check API key.")
    messages = [SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_build_case_prompt(case, transactions, rule_triggers))]
    response = llm.invoke(messages)
    raw = response.content if hasattr(response, "content") else str(response)
    return _parse_sar_output(raw, case.get("case_id", str(uuid.uuid4())))

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────
def page_login():
    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("""
        <div style="text-align:center; padding-top:80px;">
            <img src="https://img.icons8.com/color/96/bank.png" width="72" style="margin-bottom:12px"/>
            <div class="login-title">SAR Narrative Generator</div>
            <div class="login-sub">India AML Compliance Platform — PMLA 2002 / FIU-IND</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            if submitted:
                user = USERS.get(username)
                if user and user["password"] == password and user["active"]:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.current_page = "Dashboard"
                    st.rerun()
                else:
                    st.error("Invalid credentials or account inactive.")

        st.markdown("""
        <div style="background:rgba(30,136,229,0.1); border:1px solid #1e3a5f;
                    border-radius:10px; padding:14px; margin-top:16px; font-size:0.82rem; color:#90caf9;">
        <b>Demo Credentials:</b><br>
        👤 admin / Admin@2024! &nbsp;|&nbsp; analyst1 / Analyst@2024!<br>
        supervisor1 / Supervisor@2024! &nbsp;|&nbsp; readonly1 / Readonly@2024!
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR (shown after login)
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:16px 0 8px;">
            <div class="sidebar-logo">🛡️ SAR Guardian</div>
            <div style="font-size:0.7rem; color:#5c7a9e; letter-spacing:2px;">FIU-IND | PMLA 2002</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        u = current_user()
        r = u.get("role", "")
        st.markdown(f"""
        <div class="sidebar-user">
            <b style="color:#e8eaf6;">{u.get("name","")}</b><br>
            <span class="role-badge role-{r}">{r}</span>
            <br><small style="color:#5c7a9e;">{u.get("department","")}</small>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        uc = unread_count()
        if uc > 0:
            if st.button(f"⚠️  UNREAD ALERTS  ({uc})", use_container_width=True, type="secondary"):
                st.session_state.current_page = "Alerts"
                st.rerun()
            st.markdown("")

        pages = ["Dashboard", "Case Management", "Generate SAR",
                 "Review & Approve", "Alerts", "Audit Trail",
                 "Reports & Analytics"]
        if role() == "ADMIN":
            pages.append("User Management")

        icons = {"Dashboard": "📊", "Case Management": "📁", "Generate SAR": "🚀",
                 "Review & Approve": "✅", "Alerts": "🔔", "Audit Trail": "🔍",
                 "Reports & Analytics": "📈", "User Management": "👥"}

        for p in pages:
            label = f"{icons.get(p,'')}  {p}"
            active = st.session_state.current_page == p
            if st.button(label, use_container_width=True,
                         type="primary" if active else "secondary", key=f"nav_{p}"):
                st.session_state.current_page = p
                st.rerun()

        st.divider()
        if st.button("🚪  Sign Out", use_container_width=True):
            for k in ["authenticated", "username", "current_page",
                      "transactions", "rule_triggers", "sar_history",
                      "current_sar", "generation_error"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

        st.markdown(
            f"<div style='font-size:0.7rem; color:#37474f; text-align:center; margin-top:10px;'>"
            f"v2.0 | FIU-IND AML © 2024</div>",
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown("## 📊 Dashboard")
    st.markdown("**AML Compliance Overview — PMLA 2002 | FIU-IND | RBI**")
    st.divider()

    cases = st.session_state.cases
    alerts = st.session_state.alerts
    uc = unread_count()

    c1, c2, c3, c4 = st.columns(4)
    statuses = [c["status"] for c in cases]
    c1.metric("Total Cases", len(cases))
    c2.metric("In Review", statuses.count("IN_REVIEW"))
    c3.metric("Unread Alerts", uc, delta=f"+{uc}" if uc > 0 else None,
              delta_color="inverse" if uc > 0 else "off")
    c4.metric("Generated SARs", len(st.session_state.sar_history))

    st.divider()
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### 📋 Case Status Distribution")
        try:
            import plotly.graph_objects as go
            from collections import Counter
            sc = Counter(statuses)
            colours = {"DRAFT": "#37474f", "IN_REVIEW": "#1565c0",
                       "SUBMITTED": "#6a1b9a", "APPROVED": "#2e7d32"}
            fig = go.Figure(go.Pie(
                labels=list(sc.keys()), values=list(sc.values()), hole=0.5,
                marker_colors=[colours.get(k, "#1e88e5") for k in sc.keys()],
            ))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#cdd5e0", showlegend=True, height=280,
                              margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            from collections import Counter
            sc = Counter(statuses)
            import pandas as pd
            st.bar_chart(pd.Series(sc))

    with col_right:
        st.markdown("#### ⚠️ Alert Severity Distribution")
        try:
            import plotly.graph_objects as go
            from collections import Counter
            sev_c = Counter(a["severity"] for a in alerts)
            sev_colours = {"CRITICAL": "#b71c1c", "HIGH": "#e53935",
                           "MEDIUM": "#fb8c00", "LOW": "#388e3c"}
            fig2 = go.Figure(go.Bar(
                x=list(sev_c.keys()), y=list(sev_c.values()),
                marker_color=[sev_colours.get(k, "#1e88e5") for k in sev_c.keys()],
            ))
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font_color="#cdd5e0", height=280, margin=dict(t=10, b=10),
                               xaxis=dict(gridcolor="#1e3a5f"), yaxis=dict(gridcolor="#1e3a5f"))
            st.plotly_chart(fig2, use_container_width=True)
        except ImportError:
            from collections import Counter
            import pandas as pd
            sev_c = Counter(a["severity"] for a in alerts)
            st.bar_chart(pd.Series(sev_c))

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 🔔 Recent Alerts")
        for a in alerts[:3]:
            icon = "🔴" if a["severity"] == "CRITICAL" else "🟠" if a["severity"] == "HIGH" else "🟡"
            unread = "●" if not a["read"] else ""
            st.markdown(
                f"<div class='alert-card alert-{a['severity']}'>"
                f"<b>{icon} {unread} {a['title']}</b><br>"
                f"<small style='color:#90caf9;'>{a['message'][:80]}…</small><br>"
                f"<small style='color:#5c7a9e;'>{a['time']} | Case: {a['case_id']}</small>"
                f"</div>",
                unsafe_allow_html=True,
            )
        if st.button("View All Alerts →", key="dash_alerts"):
            st.session_state.current_page = "Alerts"
            st.rerun()

    with col_b:
        st.markdown("#### 📋 Recent Audit Activity")
        for entry in st.session_state.audit_log[:4]:
            st.markdown(
                f"**{entry['action']}** — {entry['user']}  \n"
                f"<small style='color:#5c7a9e;'>{entry['timestamp']} | {entry['details']}</small>",
                unsafe_allow_html=True,
            )
            st.markdown("---")

    st.markdown("#### ⚡ Quick Actions")
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        if st.button("➕ New SAR Case", use_container_width=True, type="primary"):
            st.session_state.current_page = "Generate SAR"
            st.rerun()
    with qa2:
        if st.button("✅ Review Queue", use_container_width=True):
            st.session_state.current_page = "Review & Approve"
            st.rerun()
    with qa3:
        if st.button("📊 View Reports", use_container_width=True):
            st.session_state.current_page = "Reports & Analytics"
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: CASE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
def page_case_management():
    st.markdown("## 📁 Case Management")
    st.divider()

    cases = st.session_state.cases
    import pandas as pd

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        status_filter = st.selectbox("Filter by Status",
            ["All", "DRAFT", "IN_REVIEW", "SUBMITTED", "APPROVED"])
    with col_f2:
        risk_filter = st.selectbox("Filter by Risk",
            ["All", "LOW", "MEDIUM", "HIGH", "CRITICAL"])

    filtered = [
        c for c in cases
        if (status_filter == "All" or c["status"] == status_filter)
        and (risk_filter == "All" or c["risk_rating"] == risk_filter)
    ]

    df = pd.DataFrame(filtered)
    if not df.empty:
        st.dataframe(df, use_container_width=True, height=320)
    else:
        st.info("No cases match the selected filters.")

    st.divider()
    if can_generate():
        st.markdown("#### ➕ Register New Case")
        with st.form("new_case_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                nc_id = st.text_input("Case ID", value=f"CASE-{uuid.uuid4().hex[:3].upper()}")
                nc_cust = st.text_input("Customer Name")
            with c2:
                nc_risk = st.selectbox("Risk Rating", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
                nc_alert = st.text_input("Alert Type")
            with c3:
                nc_status = st.selectbox("Status", ["DRAFT", "IN_REVIEW"])
            if st.form_submit_button("Create Case", type="primary", use_container_width=True):
                st.session_state.cases.append({
                    "case_id": nc_id, "customer_name": nc_cust,
                    "risk_rating": nc_risk, "status": nc_status,
                    "alert_type": nc_alert,
                    "created_at": datetime.now().strftime("%Y-%m-%d"),
                })
                st.success(f"Case {nc_id} created.")
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: GENERATE SAR
# ─────────────────────────────────────────────────────────────────────────────
def _sample_customers():
    return {
        "Arjun Sharma (CUST-001) [HIGH]": {
            "customer_id": "CUST-001", "customer_name": "Arjun Sharma",
            "customer_type": "individual", "customer_risk_rating": "HIGH",
            "occupation": "Import/Export Trader", "employer": "Sharma Trading Pvt Ltd",
            "annual_income": "₹85,00,000", "nationality": "Indian",
            "pep": False, "kyc_status": "VERIFIED",
            "account_number": "ACC-10012201", "account_type": "current",
            "account_balance": 12500000,
            "alerts": {
                "[HIGH] STRUCTURING | ₹4.85 Cr | ALT-2024-001": {
                    "alert_id": "ALT-2024-001", "alert_type": "STRUCTURING", "severity": "HIGH",
                    "alert_score": 94.5, "total_amount": 48500000, "txn_count": 47,
                    "date_from": "2024-01-08", "date_to": "2024-01-15",
                    "jurisdictions": ["India", "United Arab Emirates", "Singapore", "Cayman Islands"],
                    "triggering_factors": [
                        "47 incoming NEFT/RTGS transfers from different source accounts in 7 days",
                        "Immediate outbound SWIFT transfer of ₹4.85 Cr following receipt of funds",
                        "Transaction amounts structured at ₹9.5L–₹9.99L range (below ₹10L CTR threshold)",
                        "Destination account in UAE — FATF-monitored jurisdiction per RBI High-Risk List",
                        "Activity inconsistent with stated occupation and declared income of ₹85L p.a.",
                    ],
                    "transactions": [
                        {"id": str(uuid.uuid4()), "transaction_ref": "TXN-0001", "amount": 980000, "currency": "INR", "transaction_date": "2024-01-08", "transaction_type": "neft", "direction": "inbound", "counterparty_name": "Various Sources", "counterparty_bank": "SBI Mumbai", "country": "India", "purpose": "Trade payment", "is_flagged": True},
                        {"id": str(uuid.uuid4()), "transaction_ref": "TXN-0002", "amount": 995000, "currency": "INR", "transaction_date": "2024-01-09", "transaction_type": "rtgs", "direction": "inbound", "counterparty_name": "Various Sources", "counterparty_bank": "ICICI Bank Mumbai", "country": "India", "purpose": "Trade payment", "is_flagged": True},
                        {"id": str(uuid.uuid4()), "transaction_ref": "TXN-0048", "amount": 48500000, "currency": "INR", "transaction_date": "2024-01-15", "transaction_type": "swift", "direction": "outbound", "counterparty_name": "Gulf Trade LLC", "counterparty_bank": "Emirates NBD Dubai", "country": "United Arab Emirates", "purpose": "Business investment", "is_flagged": True},
                    ],
                    "rule_triggers": [
                        {"id": str(uuid.uuid4()), "rule_code": "CTR001", "rule_description": "Multiple sub-threshold NEFT/RTGS transactions to avoid CTR filing — PMLA 2002 Section 12 / RBI Master Direction on AML", "typology_code": "Structuring", "threshold_value": 1000000, "actual_value": 995000, "breached": True},
                        {"id": str(uuid.uuid4()), "rule_code": "GEO002", "rule_description": "Wire transfer to FATF-monitored high-risk jurisdiction (UAE) — RBI KYC Master Direction enhanced monitoring", "typology_code": "Jurisdiction Risk", "threshold_value": 1, "actual_value": 1, "breached": True},
                    ],
                },
            },
        },
        "Elena Petrov (CUST-002) [VERY HIGH]": {
            "customer_id": "CUST-002", "customer_name": "Elena Petrov",
            "customer_type": "PEP", "customer_risk_rating": "VERY HIGH",
            "occupation": "Government Official", "employer": "Ministry of Finance (Foreign National)",
            "annual_income": "₹3,20,00,000", "nationality": "Russian",
            "pep": True, "kyc_status": "ENHANCED DUE DILIGENCE",
            "account_number": "ACC-10023102", "account_type": "offshore",
            "account_balance": 450000000,
            "alerts": {
                "[VERY HIGH] LAYERING | ₹23.75 Cr | ALT-2024-002": {
                    "alert_id": "ALT-2024-002", "alert_type": "LAYERING", "severity": "CRITICAL",
                    "alert_score": 98.1, "total_amount": 237500000, "txn_count": 12,
                    "date_from": "2024-01-10", "date_to": "2024-01-20",
                    "jurisdictions": ["India", "Cyprus", "Cayman Islands", "British Virgin Islands"],
                    "triggering_factors": [
                        "PEP customer with 12 large offshore SWIFT transfers in 10 days",
                        "Funds routed through multiple shell company accounts in secrecy jurisdictions",
                        "Transfers to BVI and Cayman Islands — high-risk jurisdictions per RBI/FATF",
                        "No legitimate business rationale provided — PMLA Section 12(1)(b) violation",
                        "Transaction values grossly inconsistent with declared government salary",
                    ],
                    "transactions": [
                        {"id": str(uuid.uuid4()), "transaction_ref": "TXN-EP01", "amount": 79000000, "currency": "INR", "transaction_date": "2024-01-10", "transaction_type": "swift", "direction": "outbound", "counterparty_name": "Meridian Holdings Ltd", "counterparty_bank": "Bank of Cyprus", "country": "Cyprus", "purpose": "Investment", "is_flagged": True},
                        {"id": str(uuid.uuid4()), "transaction_ref": "TXN-EP02", "amount": 99500000, "currency": "INR", "transaction_date": "2024-01-15", "transaction_type": "swift", "direction": "outbound", "counterparty_name": "Sunridge BVI Inc", "counterparty_bank": "BVI Offshore Bank", "country": "British Virgin Islands", "purpose": "Loan repayment", "is_flagged": True},
                    ],
                    "rule_triggers": [
                        {"id": str(uuid.uuid4()), "rule_code": "PEP001", "rule_description": "PEP high-value transaction without EDD clearance — PMLA 2002 Section 12(1)(b) and RBI KYC Master Circular on PEP", "typology_code": "PEP Risk", "threshold_value": 10000000, "actual_value": 79000000, "breached": True},
                        {"id": str(uuid.uuid4()), "rule_code": "LAY003", "rule_description": "Layering through offshore shell companies — FATF Recommendation 20, PMLA Section 3 predicate offence risk", "typology_code": "Layering", "threshold_value": 3, "actual_value": 12, "breached": True},
                    ],
                },
            },
        },
        "Mohammed Al-Rashid (CUST-003) [HIGH]": {
            "customer_id": "CUST-003", "customer_name": "Mohammed Al-Rashid",
            "customer_type": "individual", "customer_risk_rating": "HIGH",
            "occupation": "Real Estate Developer", "employer": "Al-Rashid Properties Pvt Ltd",
            "annual_income": "₹5,00,00,000", "nationality": "Saudi Arabian",
            "pep": False, "kyc_status": "VERIFIED",
            "account_number": "ACC-10034503", "account_type": "current",
            "account_balance": 89000000,
            "alerts": {
                "[HIGH] SMURFING | ₹9.80 L | ALT-2024-003": {
                    "alert_id": "ALT-2024-003", "alert_type": "SMURFING", "severity": "HIGH",
                    "alert_score": 88.7, "total_amount": 980000, "txn_count": 32,
                    "date_from": "2024-01-05", "date_to": "2024-01-12",
                    "jurisdictions": ["India", "United Arab Emirates", "Saudi Arabia"],
                    "triggering_factors": [
                        "32 cash deposits below ₹50,000 threshold within 7 days across multiple branches",
                        "Deposits made at 11 different HDFC Bank branch locations in Mumbai",
                        "Total structured amount of ₹9.8L approaches ₹10L CTR reporting threshold",
                        "Pattern consistent with smurfing typology per FIU-IND Advisory No. 2022-03",
                        "Cash deposit pattern inconsistent with customer's declared real estate business",
                    ],
                    "transactions": [
                        {"id": str(uuid.uuid4()), "transaction_ref": "TXN-AR01", "amount": 49500, "currency": "INR", "transaction_date": "2024-01-05", "transaction_type": "cash", "direction": "inbound", "counterparty_name": "Cash Deposit", "counterparty_bank": "HDFC Bank Mumbai – Andheri Branch", "country": "India", "purpose": "Business income", "is_flagged": True},
                        {"id": str(uuid.uuid4()), "transaction_ref": "TXN-AR02", "amount": 49800, "currency": "INR", "transaction_date": "2024-01-06", "transaction_type": "cash", "direction": "inbound", "counterparty_name": "Cash Deposit", "counterparty_bank": "HDFC Bank Pune – FC Road Branch", "country": "India", "purpose": "Business income", "is_flagged": True},
                    ],
                    "rule_triggers": [
                        {"id": str(uuid.uuid4()), "rule_code": "SMRF003", "rule_description": "Multiple sub-threshold cash deposits (smurfing) — FIU-IND Advisory on Structuring/Smurfing, PMLA Section 3", "typology_code": "Smurfing", "threshold_value": 50000, "actual_value": 49800, "breached": True},
                    ],
                },
            },
        },
        "Li Wei Chen (CUST-004) [MEDIUM]": {
            "customer_id": "CUST-004", "customer_name": "Li Wei Chen",
            "customer_type": "entity", "customer_risk_rating": "MEDIUM",
            "occupation": "Technology Consulting", "employer": "SinoTech Solutions Pvt Ltd",
            "annual_income": "₹2,00,00,000", "nationality": "Chinese",
            "pep": False, "kyc_status": "VERIFIED",
            "account_number": "ACC-10045804", "account_type": "current",
            "account_balance": 34000000,
            "alerts": {
                "[MEDIUM] VELOCITY SPIKE | ₹1.25 Cr | ALT-2024-004": {
                    "alert_id": "ALT-2024-004", "alert_type": "VELOCITY SPIKE", "severity": "MEDIUM",
                    "alert_score": 72.3, "total_amount": 12500000, "txn_count": 18,
                    "date_from": "2024-01-18", "date_to": "2024-01-25",
                    "jurisdictions": ["India", "China", "Singapore"],
                    "triggering_factors": [
                        "RTGS/SWIFT transaction velocity 4.1x above 90-day moving average",
                        "Sudden large outward remittances to China without corresponding business contracts",
                        "No corresponding increase in declared business revenue — unusual for IT services",
                        "SWIFT transfers to newly registered counterparties flagged by RBI velocity monitoring",
                    ],
                    "transactions": [
                        {"id": str(uuid.uuid4()), "transaction_ref": "TXN-LW01", "amount": 4500000, "currency": "INR", "transaction_date": "2024-01-18", "transaction_type": "swift", "direction": "outbound", "counterparty_name": "Shanghai Tech Co", "counterparty_bank": "Bank of China Shanghai", "country": "China", "purpose": "Service fees", "is_flagged": True},
                    ],
                    "rule_triggers": [
                        {"id": str(uuid.uuid4()), "rule_code": "VELOC005", "rule_description": "RTGS/SWIFT velocity 4x above 90-day average — RBI AML/CFT Policy velocity monitoring threshold breached", "typology_code": "Velocity", "threshold_value": 3, "actual_value": 4.1, "breached": True},
                    ],
                },
            },
        },
        "Obiageli Nwosu (CUST-005) [HIGH]": {
            "customer_id": "CUST-005", "customer_name": "Obiageli Nwosu",
            "customer_type": "individual", "customer_risk_rating": "HIGH",
            "occupation": "NGO Director", "employer": "Global Aid Foundation India",
            "annual_income": "₹1,50,00,000", "nationality": "Nigerian",
            "pep": False, "kyc_status": "VERIFIED",
            "account_number": "ACC-10056705", "account_type": "savings",
            "account_balance": 21500000,
            "alerts": {
                "[HIGH] TRADE FINANCE FRAUD | ₹34 Cr | ALT-2024-005": {
                    "alert_id": "ALT-2024-005", "alert_type": "TRADE FINANCE FRAUD", "severity": "HIGH",
                    "alert_score": 91.2, "total_amount": 340000000, "txn_count": 8,
                    "date_from": "2024-01-20", "date_to": "2024-01-28",
                    "jurisdictions": ["Nigeria", "India", "UAE", "Singapore"],
                    "triggering_factors": [
                        "Invoices for non-existent goods used to justify large SWIFT transfers",
                        "Multiple round-number INR transfers inconsistent with NGO trade patterns",
                        "Counterparty flagged in previous STR filings with FIU-IND",
                        "NGO/savings account used for apparent high-value commercial trade activity",
                    ],
                    "transactions": [
                        {"id": str(uuid.uuid4()), "transaction_ref": "TXN-ON01", "amount": 99900000, "currency": "INR", "transaction_date": "2024-01-20", "transaction_type": "swift", "direction": "inbound", "counterparty_name": "Lagos Trading Co", "counterparty_bank": "Zenith Bank Nigeria", "country": "Nigeria", "purpose": "Aid contribution", "is_flagged": True},
                        {"id": str(uuid.uuid4()), "transaction_ref": "TXN-ON02", "amount": 99900000, "currency": "INR", "transaction_date": "2024-01-21", "transaction_type": "swift", "direction": "outbound", "counterparty_name": "Falcon Investments", "counterparty_bank": "Standard Chartered UAE", "country": "United Arab Emirates", "purpose": "Grant disbursement", "is_flagged": True},
                    ],
                    "rule_triggers": [
                        {"id": str(uuid.uuid4()), "rule_code": "TFF007", "rule_description": "Suspected trade finance fraud — invoice mismatch per RBI/SEBI Trade Finance AML Guidelines and PMLA Section 12 STR obligation", "typology_code": "Trade Finance Fraud", "threshold_value": 50000000, "actual_value": 99900000, "breached": True},
                    ],
                },
            },
        },
    }


def page_generate_sar():
    if not can_generate():
        st.warning("🔒 Read-only access: SAR generation requires ANALYST or ADMIN role.")
        return

    # Auto-load API key from secrets
    try:
        _secret_key = (st.secrets.get("GROQ_API_KEY") or st.secrets.get("OPENAI_API_KEY", ""))
        _secret_provider = "Groq" if st.secrets.get("GROQ_API_KEY") else ("OpenAI" if st.secrets.get("OPENAI_API_KEY") else None)
    except Exception:
        _secret_key = ""
        _secret_provider = None
    if _secret_key:
        if not st.session_state.get("_api_key"):
            st.session_state["_api_key"] = _secret_key
        if not st.session_state.get("provider"):
            st.session_state["provider"] = _secret_provider
    else:
        with st.expander("🔑 LLM Configuration", expanded=not bool(st.session_state.get("_api_key"))):
            st.selectbox("Provider", ["Groq", "OpenAI"], key="provider")
            st.text_input("API Key", type="password",
                          placeholder="gsk_..." if st.session_state.get("provider", "Groq") == "Groq" else "sk-...",
                          key="_api_key")

    st.markdown("""
    <div style="background:linear-gradient(90deg,#0d2244,#1a3a6e);border-radius:10px;padding:20px 28px;margin-bottom:20px;">
        <div style="font-size:1.6rem;font-weight:800;color:#fff;">🧾 STR / SAR Narrative Generator</div>
        <div style="color:#90caf9;font-size:0.95rem;margin-top:4px;">AI-powered STR narrative generation — PMLA 2002 | FIU-IND | RBI compliant</div>
    </div>
    """, unsafe_allow_html=True)

    tab_alert, tab_manual = st.tabs(["🔔 Generate from Alert", "✍️ Manual Entry"])

    CUSTOMERS = _sample_customers()

    # ── TAB 1: GENERATE FROM ALERT ──────────────────────────────────────────
    with tab_alert:
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("### 1️⃣ Select Customer & Alert")
            selected_cust_key = st.selectbox("Customer", list(CUSTOMERS.keys()), key="sel_cust")
            cust = CUSTOMERS[selected_cust_key]

            alert_keys = list(cust["alerts"].keys())
            selected_alert_key = st.selectbox("Transaction Alert", alert_keys, key="sel_alert")
            alert = cust["alerts"][selected_alert_key]

            st.markdown("**Customer Profile**")
            risk_color = {"HIGH": "#e65100", "VERY HIGH": "#b71c1c", "CRITICAL": "#b71c1c",
                          "MEDIUM": "#f57c00", "LOW": "#2e7d32"}.get(cust["customer_risk_rating"], "#888")
            st.markdown(f"""
            <div style="background:#0d2244;border:1px solid #1e3a5f;border-radius:10px;padding:16px;margin-top:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-size:1.1rem;font-weight:700;color:#e8eaf6;">{cust['customer_name']}</span>
                    <span style="background:{risk_color};color:#fff;padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">{cust['customer_risk_rating']}</span>
                </div>
                <div style="margin-top:10px;color:#cdd5e0;font-size:0.88rem;line-height:1.9;">
                    🏢 {cust['occupation']} @ {cust['employer']}<br>
                    💰 Annual Income: {cust['annual_income']}<br>
                    🌍 Nationality: {cust['nationality']}<br>
                    {'✅' if not cust['pep'] else '⚠️'} {'Non-PEP' if not cust['pep'] else 'PEP'} | KYC: {cust['kyc_status']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_right:
            st.markdown("### 2️⃣ Alert Details")
            sev_color = {"CRITICAL": "#b71c1c", "HIGH": "#e65100", "MEDIUM": "#f57c00", "LOW": "#2e7d32"}.get(alert["severity"], "#888")
            factors_html = "".join(f"<li style='margin-bottom:6px;'>{f}</li>" for f in alert["triggering_factors"])
            jur_str = ", ".join(alert["jurisdictions"])
            st.markdown(f"""
            <div style="background:#fff8e1;border-left:5px solid {sev_color};border-radius:8px;padding:16px;margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:800;font-size:1rem;color:#1a1a1a;">{alert['alert_type']}</span>
                    <span style="background:{sev_color};color:#fff;padding:3px 12px;border-radius:20px;font-size:0.76rem;font-weight:700;">{alert['severity']}</span>
                </div>
                <div style="margin-top:10px;color:#333;font-size:0.88rem;line-height:1.9;">
                    🔥 Total: <b>{format_inr(alert['total_amount'])}</b> across {alert['txn_count']} transactions<br>
                    📅 {alert['date_from']} → {alert['date_to']}<br>
                    🌍 Jurisdictions: {jur_str}<br>
                    📊 Alert Score: <b>{alert['alert_score']}/100</b>
                </div>
            </div>
            <div style="margin-top:12px;color:#1a1a1a;">
                <b>Triggering Factors:</b>
                <ul style="margin-top:8px;color:#333;font-size:0.9rem;">{factors_html}</ul>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        ak = st.session_state.get("_api_key", "")
        if not ak:
            st.warning("⚠️ No API key configured. Add GROQ_API_KEY to Streamlit secrets.")
        if st.button("🚀 Generate SAR Narrative from Alert", type="primary", use_container_width=True, disabled=not bool(ak)):
            case_dict = {
                "case_id": f"SAR-{uuid.uuid4().hex[:8].upper()}",
                "customer_id": cust["customer_id"],
                "customer_name": cust["customer_name"],
                "customer_type": cust["customer_type"],
                "customer_risk_rating": cust["customer_risk_rating"],
                "account_number": cust["account_number"],
                "account_type": cust["account_type"],
                "account_balance": cust["account_balance"],
                "alert_id": alert["alert_id"],
                "alert_type": alert["alert_type"],
                "alert_score": alert["alert_score"],
                "analyst_notes": f"Triggering factors: {'; '.join(alert['triggering_factors'])}",
            }
            with st.spinner("🔄 Calling LLM… 15–30 seconds"):
                try:
                    result = generate_sar(case_dict, alert["transactions"],
                                          alert["rule_triggers"], ak,
                                          st.session_state.get("provider", "Groq"))
                    st.session_state.current_sar = result
                    st.session_state.sar_history.append(result)
                    st.session_state.generation_error = None
                    sev = result.get("severity", "UNKNOWN")
                    st.session_state.alerts.insert(0, {
                        "id": f"ALT-{uuid.uuid4().hex[:4].upper()}",
                        "severity": sev, "title": f"SAR Generated – {case_dict['case_id']}",
                        "message": f"New SAR narrative for {cust['customer_name']}. Severity: {sev}",
                        "time": "just now", "read": False, "case_id": case_dict["case_id"],
                    })
                    st.success("✅ SAR generated successfully! See output below.")
                except Exception as exc:
                    st.session_state.generation_error = str(exc)
                    st.error(f"Generation failed: {exc}")

        _render_sar_output()

    # ── TAB 2: MANUAL ENTRY ──────────────────────────────────────────────────
    with tab_manual:
        tab_case, tab_txn, tab_rules, tab_gen = st.tabs(
            ["📁 Case Details", "💸 Transactions", "⚠️ Rule Triggers", "🚀 Generate"])

        with tab_case:
            st.markdown('<div class="section-header">Customer & Case Information</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Case ID", value=f"CASE-{uuid.uuid4().hex[:8].upper()}", key="case_id_input")
                st.text_input("Customer ID", placeholder="CUST-001", key="cust_id")
                st.text_input("Customer Name", placeholder="John Doe", key="cust_name")
                st.selectbox("Customer Type", ["individual", "entity", "PEP", "correspondent_bank"], key="cust_type")
                st.selectbox("Customer Risk Rating", ["LOW", "MEDIUM", "HIGH", "CRITICAL"], key="risk_rating")
            with col2:
                st.text_input("Account Number", placeholder="ACC-123456", key="acc_num")
                st.selectbox("Account Type", ["savings", "current", "offshore", "correspondent"], key="acc_type")
                st.number_input("Account Balance (INR)", min_value=0.0, step=1000.0, key="acc_bal")
                st.text_input("Alert ID", placeholder="ALT-2024-001", key="alert_id_input")
                st.text_input("Alert Type", placeholder="e.g. Structuring, Layering", key="alert_type_input")
                st.slider("Alert Score (0–100)", 0, 100, 75, key="alert_score")
            st.text_area("Analyst Notes", placeholder="Additional context for the LLM…",
                         height=100, key="analyst_notes")

        with tab_txn:
            st.markdown('<div class="section-header">Add Transactions</div>', unsafe_allow_html=True)
            with st.form("txn_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    txn_ref = st.text_input("Transaction Ref", placeholder="TXN-001")
                    txn_amount = st.number_input("Amount", min_value=0.0, step=500.0)
                    txn_curr = st.selectbox("Currency", ["INR","USD","EUR","GBP","AED","SGD"])
                with c2:
                    txn_date = st.date_input("Date")
                    txn_type = st.selectbox("Type", ["wire","cash","ach","swift","upi","rtgs","neft","crypto"])
                    txn_dir  = st.selectbox("Direction", ["outbound","inbound"])
                with c3:
                    cpty = st.text_input("Counterparty Name")
                    cpty_bank = st.text_input("Counterparty Bank")
                    country = st.text_input("Country")
                    flagged = st.checkbox("Flagged")
                purpose = st.text_input("Purpose / Narration")
                if st.form_submit_button("➕ Add Transaction", type="primary", use_container_width=True):
                    st.session_state.transactions.append({
                        "id": str(uuid.uuid4()),
                        "transaction_ref": txn_ref or f"TXN-{len(st.session_state.transactions)+1:03d}",
                        "amount": txn_amount, "currency": txn_curr,
                        "transaction_date": str(txn_date), "transaction_type": txn_type,
                        "direction": txn_dir, "counterparty_name": cpty,
                        "counterparty_bank": cpty_bank, "country": country,
                        "purpose": purpose, "is_flagged": flagged,
                    })
                    st.success(f"Added. Total: {len(st.session_state.transactions)}")

            if st.session_state.transactions:
                import pandas as pd
                df = pd.DataFrame(st.session_state.transactions)
                cols = ["transaction_ref","amount","currency","transaction_date",
                        "transaction_type","direction","counterparty_name","country","is_flagged"]
                st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Value (INR)", format_inr(sum(t['amount'] for t in st.session_state.transactions)))
                m2.metric("Flagged", sum(1 for t in st.session_state.transactions if t.get("is_flagged")))
                m3.metric("Countries", len(set(t.get("country","") for t in st.session_state.transactions if t.get("country"))))
                if st.button("🗑️ Clear All Transactions"):
                    st.session_state.transactions = []
                    st.rerun()

        with tab_rules:
            SAMPLE_RULES = {
                "CTR001 – Cash threshold breach (PMLA ₹10L)":   ("CTR001","Cash transaction ≥ ₹10L — CTR filing mandatory per PMLA 2002 Section 12 / RBI Master Direction","Structuring",1000000),
                "STR001 – Suspicious transaction report":        ("STR001","Transaction inconsistent with customer profile — STR filing to FIU-IND under PMLA Section 12","Suspicious Activity",500000),
                "LAY002 – Layering via offshore SWIFT":          ("LAY002","Multiple offshore SWIFT transfers within 72h — FATF Recommendation 20, PMLA Section 3","Layering",3),
                "SMRF003 – Smurfing / structuring pattern":      ("SMRF003","Multiple sub-threshold cash deposits to avoid CTR — FIU-IND Smurfing Advisory 2022","Smurfing",990000),
                "PEP004 – PEP high-risk transaction":            ("PEP004","PEP high-value transaction without EDD — RBI KYC Master Circular 2016 (Updated 2023)","PEP Risk",500000),
                "VELOC005 – Velocity spike (RBI monitoring)":    ("VELOC005","RTGS/NEFT velocity 3x above 90-day avg — RBI AML/CFT velocity monitoring rule","Velocity",3),
                "GEO006 – High-risk jurisdiction transfer":      ("GEO006","Wire transfer to FATF High-Risk / RBI Watch-list jurisdiction — enhanced due diligence required","Jurisdiction Risk",1),
                "CUSTOM – Enter manually": None,
            }
            preset = st.selectbox("Quick-fill from common rules", list(SAMPLE_RULES.keys()))
            prefill = SAMPLE_RULES.get(preset)
            with st.form("rule_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    rule_code = st.text_input("Rule Code", value=prefill[0] if prefill else "")
                    rule_desc = st.text_input("Description", value=prefill[1] if prefill else "")
                    typology  = st.text_input("Typology", value=prefill[2] if prefill else "")
                with c2:
                    threshold  = st.number_input("Threshold", value=float(prefill[3]) if prefill else 0.0)
                    actual_val = st.number_input("Actual Value", min_value=0.0, step=1.0)
                    breached   = st.checkbox("Threshold Breached", value=True)
                if st.form_submit_button("➕ Add Rule Trigger", type="primary", use_container_width=True):
                    st.session_state.rule_triggers.append({
                        "id": str(uuid.uuid4()),
                        "rule_code": rule_code, "rule_description": rule_desc,
                        "typology_code": typology, "threshold_value": threshold,
                        "actual_value": actual_val, "breached": breached,
                    })
                    st.success(f"Added. Total: {len(st.session_state.rule_triggers)}")
            if st.session_state.rule_triggers:
                import pandas as pd
                st.dataframe(pd.DataFrame(st.session_state.rule_triggers)
                             [["rule_code","rule_description","typology_code","threshold_value","actual_value","breached"]],
                             use_container_width=True)
                if st.button("🗑️ Clear All Rules"):
                    st.session_state.rule_triggers = []
                    st.rerun()

        with tab_gen:
            warnings_list = []
            ak = st.session_state.get("_api_key","")
            if not ak: warnings_list.append("⚠️ No API key configured. Add GROQ_API_KEY to Streamlit secrets.")
            if not st.session_state.transactions: warnings_list.append("⚠️ No transactions added.")
            if not st.session_state.rule_triggers: warnings_list.append("⚠️ No rule triggers added.")
            for w in warnings_list: st.warning(w)

            st.markdown(
                f"Ready: **{st.session_state.get('cust_name','(unnamed)')}** | "
                f"Transactions: **{len(st.session_state.transactions)}** | "
                f"Rules breached: **{sum(1 for r in st.session_state.rule_triggers if r.get('breached'))}**"
            )

            if st.button("🚀 Generate SAR Narrative", type="primary", use_container_width=True,
                         disabled=not bool(ak)):
                case_dict = {
                    "case_id": st.session_state.get("case_id_input",""),
                    "customer_id": st.session_state.get("cust_id",""),
                    "customer_name": st.session_state.get("cust_name",""),
                    "customer_type": st.session_state.get("cust_type",""),
                    "customer_risk_rating": st.session_state.get("risk_rating",""),
                    "account_number": st.session_state.get("acc_num",""),
                    "account_type": st.session_state.get("acc_type",""),
                    "account_balance": st.session_state.get("acc_bal",0),
                    "alert_id": st.session_state.get("alert_id_input",""),
                    "alert_type": st.session_state.get("alert_type_input",""),
                    "alert_score": st.session_state.get("alert_score",0),
                    "analyst_notes": st.session_state.get("analyst_notes",""),
                }
                with st.spinner("🔄 Calling LLM… 15–30 seconds"):
                    try:
                        result = generate_sar(case_dict, st.session_state.transactions,
                                              st.session_state.rule_triggers, ak,
                                              st.session_state.get("provider","Groq"))
                        st.session_state.current_sar = result
                        st.session_state.sar_history.append(result)
                        st.session_state.generation_error = None
                        sev = result.get("severity","UNKNOWN")
                        st.session_state.alerts.insert(0, {
                            "id": f"ALT-{uuid.uuid4().hex[:4].upper()}",
                            "severity": sev, "title": f"SAR Generated – {case_dict['case_id']}",
                            "message": f"New SAR narrative for {case_dict['customer_name']}. Severity: {sev}",
                            "time": "just now", "read": False, "case_id": case_dict["case_id"],
                        })
                        st.success("✅ SAR generated successfully!")
                    except Exception as exc:
                        st.session_state.generation_error = str(exc)
                        st.error(f"Generation failed: {exc}")

            _render_sar_output()


def _render_sar_output():
    if st.session_state.generation_error:
        st.error(st.session_state.generation_error)
    if st.session_state.current_sar:
        sar = st.session_state.current_sar
        sev = sar.get("severity","UNKNOWN")
        st.divider()
        s1, s2, s3 = st.columns(3)
        s1.markdown(f'**Severity:** <span class="sev-{sev}">{sev}</span>', unsafe_allow_html=True)
        s2.metric("Sentences", len(sar.get("sentences_with_hashes",[])))
        s3.metric("Generated", sar.get("generated_at","")[:19].replace("T"," "))
        st.markdown('<div class="section-header">📄 Section A — SAR Draft Narrative</div>', unsafe_allow_html=True)
        st.markdown(sar["narrative"])
        st.divider()
        st.markdown('<div class="section-header">🔒 Sentence-Level SHA-256 Hashes</div>', unsafe_allow_html=True)
        for entry in sar.get("sentences_with_hashes",[]):
            with st.expander(entry["sentence"][:100]+("…" if len(entry["sentence"])>100 else ""), expanded=False):
                st.markdown(f'<div class="hash-box">{entry["hash"]}</div>', unsafe_allow_html=True)
        audit_str = json.dumps({"hashes": sar.get("sentences_with_hashes",[]), "audit": sar.get("audit",{})},
                               indent=2, default=str)
        st.download_button("⬇️ Download Audit JSON", data=audit_str,
                           file_name=f"SAR_audit_{sar['case_id']}.json",
                           mime="application/json", use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: REVIEW & APPROVE
# ─────────────────────────────────────────────────────────────────────────────
def page_review():
    st.markdown("## ✅ Review & Approve")
    if not can_approve():
        st.warning("🔒 Review & Approve requires SUPERVISOR or ADMIN role.")
    st.divider()

    queue = [c for c in st.session_state.cases if c["status"] == "IN_REVIEW"]
    if not queue:
        st.info("No cases currently in the review queue.")
        return

    for c in queue:
        with st.expander(f"📁 {c['case_id']} — {c['customer_name']} | Risk: {c['risk_rating']}", expanded=True):
            col1, col2, col3 = st.columns(3)
            col1.metric("Risk Rating", c["risk_rating"])
            col2.metric("Alert Type", c["alert_type"])
            col3.metric("Created", c["created_at"])
            if can_approve():
                ac1, ac2, ac3 = st.columns(3)
                if ac1.button("✅ Approve", key=f"app_{c['case_id']}", type="primary"):
                    c["status"] = "APPROVED"
                    st.session_state.audit_log.insert(0, {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "user": st.session_state.username,
                        "action": "SAR_APPROVED", "case_id": c["case_id"],
                        "details": f"Approved by {current_user().get('name','')}",
                    })
                    st.success(f"{c['case_id']} approved.")
                    st.rerun()
                if ac2.button("❌ Reject", key=f"rej_{c['case_id']}"):
                    c["status"] = "DRAFT"
                    st.warning(f"{c['case_id']} sent back to Draft.")
                    st.rerun()
                if ac3.button("📤 Submit to Regulator", key=f"sub_{c['case_id']}"):
                    c["status"] = "SUBMITTED"
                    st.success(f"{c['case_id']} submitted.")
                    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ALERTS CENTRE
# ─────────────────────────────────────────────────────────────────────────────
def page_alerts():
    st.markdown("## 🔔 Alerts Centre")
    st.divider()

    alerts = st.session_state.alerts
    uc = unread_count()

    # Controls row
    f1, f2, f3 = st.columns([1.5, 1.5, 2])
    with f1:
        sev_filter  = st.selectbox("Filter by Severity", ["All","CRITICAL","HIGH","MEDIUM","LOW"], key="af_sev")
    with f2:
        read_filter = st.selectbox("Filter by Status", ["All","Unread","Read"], key="af_read")
    with f3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button(f"✓ Mark All as Read  ({uc} unread)", type="primary", use_container_width=True):
            for a in st.session_state.alerts:
                a["read"] = True
            st.success("All alerts marked as read.")
            st.rerun()

    st.markdown(f"**{uc} unread** of {len(alerts)} total alerts")
    st.divider()

    # Filter
    filtered = [
        a for a in alerts
        if (sev_filter  == "All" or a["severity"] == sev_filter)
        and (read_filter == "All"
             or (read_filter == "Unread" and not a["read"])
             or (read_filter == "Read"   and a["read"]))
    ]

    if not filtered:
        st.info("No alerts match the selected filters.")
        return

    sev_icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}

    for a in filtered:
        icon  = sev_icons.get(a["severity"], "⚪")
        unread_indicator = '<span class="unread-dot"></span>' if not a["read"] else ""

        col_card, col_btn = st.columns([5, 1])
        with col_card:
            st.markdown(
                f"<div class='alert-card alert-{a['severity']}'>"
                f"<div style='font-weight:700; font-size:1rem;'>"
                f"{icon} {unread_indicator}{a['title']}"
                f"  <span class='sev-{a['severity']}'>{a['severity']}</span>"
                f"</div>"
                f"<div style='margin-top:6px; color:#cdd5e0;'>{html.escape(str(a['message']))}</div>"
                f"<div style='margin-top:8px; font-size:0.8rem; color:#5c7a9e;'>"
                f"🕐 {a['time']}  |  Case: {a['case_id']}  |  ID: {a['id']}"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            if not a["read"]:
                if st.button("Mark Read", key=f"mr_{a['id']}", use_container_width=True):
                    for alert in st.session_state.alerts:
                        if alert["id"] == a["id"]:
                            alert["read"] = True
                    st.rerun()
            else:
                st.markdown("<small style='color:#5c7a9e;'>✓ Read</small>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: AUDIT TRAIL
# ─────────────────────────────────────────────────────────────────────────────
def page_audit_trail():
    st.markdown("## 🔍 Audit Trail")
    st.divider()

    import pandas as pd
    tab_log, tab_hash = st.tabs(["📋 Activity Log", "🔒 Hash Verification"])

    with tab_log:
        log = st.session_state.audit_log
        if log:
            df = pd.DataFrame(log)
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No audit log entries yet.")

    with tab_hash:
        if not st.session_state.sar_history:
            st.info("Generate a SAR first to verify its hash integrity.")
        else:
            sar = st.session_state.sar_history[-1]
            st.markdown(f"**Verifying:** Case `{sar['case_id']}` generated at `{sar['generated_at'][:19]}`")
            st.divider()
            all_ok = True
            for entry in sar.get("sentences_with_hashes", []):
                recomputed = sha256(entry["sentence"])
                ok = recomputed == entry["hash"]
                if not ok:
                    all_ok = False
                status = "✅ VALID" if ok else "❌ TAMPERED"
                with st.expander(f"{status}  {entry['sentence'][:80]}…", expanded=False):
                    st.markdown(f"**Stored:**     `{entry['hash']}`")
                    st.markdown(f"**Recomputed:** `{recomputed}`")
                    if not ok:
                        st.error("Hash mismatch — sentence may have been tampered with!")

            if all_ok:
                st.success(f"✅ All {len(sar.get('sentences_with_hashes',[]))} sentence hashes verified — document integrity intact.")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: REPORTS & ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
def page_reports():
    st.markdown("## 📈 Reports & Analytics")
    st.divider()

    cases  = st.session_state.cases
    alerts = st.session_state.alerts

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Cases", len(cases))
    m2.metric("Total Alerts", len(alerts))
    m3.metric("SARs Generated", len(st.session_state.sar_history))
    m4.metric("Approved Cases", sum(1 for c in cases if c["status"] == "APPROVED"))
    st.divider()

    try:
        import plotly.graph_objects as go
        from collections import Counter
        import pandas as pd

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Cases by Risk Rating")
            rc = Counter(c["risk_rating"] for c in cases)
            fig = go.Figure(go.Bar(
                x=list(rc.keys()), y=list(rc.values()),
                marker_color=["#388e3c","#fb8c00","#e53935","#b71c1c"],
            ))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#cdd5e0", height=260, margin=dict(t=10,b=10),
                              xaxis=dict(gridcolor="#1e3a5f"), yaxis=dict(gridcolor="#1e3a5f"))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("#### Alert Type Distribution")
            ac = Counter(c["alert_type"] for c in cases)
            fig2 = go.Figure(go.Pie(labels=list(ac.keys()), values=list(ac.values()), hole=0.4))
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font_color="#cdd5e0", height=260, margin=dict(t=10,b=10))
            st.plotly_chart(fig2, use_container_width=True)
    except ImportError:
        st.info("Install plotly for charts: `pip install plotly`")

    st.divider()
    import pandas as pd
    st.markdown("#### Export Data")
    ec1, ec2 = st.columns(2)
    with ec1:
        st.download_button(
            "⬇️ Export Cases (JSON)", data=json.dumps(cases, indent=2, default=str),
            file_name="cases_export.json", mime="application/json", use_container_width=True,
        )
    with ec2:
        st.download_button(
            "⬇️ Export Audit Log (JSON)", data=json.dumps(st.session_state.audit_log, indent=2, default=str),
            file_name="audit_log_export.json", mime="application/json", use_container_width=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: USER MANAGEMENT (ADMIN only)
# ─────────────────────────────────────────────────────────────────────────────
def page_user_management():
    st.markdown("## 👥 User Management")
    if role() != "ADMIN":
        st.error("🔒 Admin access required.")
        return
    st.divider()

    import pandas as pd
    users_data = [
        {"username": u, "name": d["name"], "role": d["role"],
         "department": d["department"], "active": d["active"]}
        for u, d in st.session_state.users.items()
    ]
    df = pd.DataFrame(users_data)
    st.dataframe(df, use_container_width=True)

    st.divider()
    st.markdown("#### Toggle User Status")
    user_to_toggle = st.selectbox("Select user", [u for u in st.session_state.users if u != st.session_state.username])
    u_data = st.session_state.users.get(user_to_toggle, {})
    st.markdown(f"**{user_to_toggle}** – Currently: {'✅ Active' if u_data.get('active') else '🔴 Inactive'}")
    if st.button("Toggle Status", type="primary"):
        st.session_state.users[user_to_toggle]["active"] = not u_data.get("active", True)
        st.success(f"{user_to_toggle} status updated.")
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    page_login()
else:
    render_sidebar()

    page = st.session_state.current_page
    if   page == "Dashboard":          page_dashboard()
    elif page == "Case Management":    page_case_management()
    elif page == "Generate SAR":       page_generate_sar()
    elif page == "Review & Approve":   page_review()
    elif page == "Alerts":             page_alerts()
    elif page == "Audit Trail":        page_audit_trail()
    elif page == "Reports & Analytics": page_reports()
    elif page == "User Management":    page_user_management()
    else:
        st.error(f"Unknown page: {page}")

    # Footer
    st.divider()
    st.markdown(
        "<small>⚖️ **Disclaimer:** AI-assisted STR/SAR drafts for compliance review only — PMLA 2002 / FIU-IND. "
        "All outputs require review and approval by a qualified PMLA Compliance Officer before submission to FIU-IND.</small>",
        unsafe_allow_html=True,
    )
