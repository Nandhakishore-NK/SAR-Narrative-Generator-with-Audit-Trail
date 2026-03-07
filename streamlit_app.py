"""
SAR Narrative Generator with Audit Trail
Barclays AML Compliance Platform
=========================================
Multi-page Streamlit app: login, role-based sidebar navigation, dashboard,
case management, SAR generation, review & approve, alerts centre, audit trail,
reports & analytics, and user management.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone, timedelta

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page config (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SAR Guardian – Barclays AML",
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
        "name": "Sarah Johnson",
        "role": "ANALYST",
        "department": "AML Compliance",
        "active": True,
    },
    "supervisor1": {
        "password": "Supervisor@2024!",
        "name": "David Chen",
        "role": "SUPERVISOR",
        "department": "AML Compliance",
        "active": True,
    },
    "readonly1": {
        "password": "Readonly@2024!",
        "name": "Emma Williams",
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
        {"case_id": "CASE-002", "customer_name": "Offshore Holdings Ltd", "risk_rating": "CRITICAL",
         "status": "SUBMITTED", "alert_type": "Layering", "created_at": "2024-01-18"},
        {"case_id": "CASE-003", "customer_name": "Maria Santos", "risk_rating": "MEDIUM",
         "status": "DRAFT", "alert_type": "Velocity Spike", "created_at": "2024-01-20"},
        {"case_id": "CASE-004", "customer_name": "Tech Ventures Inc", "risk_rating": "HIGH",
         "status": "APPROVED", "alert_type": "PEP Risk", "created_at": "2024-01-22"},
        {"case_id": "CASE-005", "customer_name": "Hassan Al-Rashid", "risk_rating": "CRITICAL",
         "status": "IN_REVIEW", "alert_type": "Smurfing", "created_at": "2024-01-25"},
    ]

def _sample_alerts():
    return [
        {"id": "ALT-001", "severity": "CRITICAL", "title": "Smurfing Pattern Detected",
         "message": "Customer CUST-0891 shows 47 sub-threshold deposits in 72 hours totalling ₹48L.",
         "time": "2 min ago", "read": False, "case_id": "CASE-005"},
        {"id": "ALT-002", "severity": "HIGH", "title": "Offshore Wire Transfer Alert",
         "message": "Multiple SWIFT transfers to UAE counterparty flagged. Total: $2.3M.",
         "time": "15 min ago", "read": False, "case_id": "CASE-002"},
        {"id": "ALT-003", "severity": "HIGH", "title": "PEP Transaction Flagged",
         "message": "Politically Exposed Person transaction ₹15L — requires enhanced due diligence.",
         "time": "1 hr ago", "read": False, "case_id": "CASE-004"},
        {"id": "ALT-004", "severity": "MEDIUM", "title": "Velocity Threshold Breach",
         "message": "Transaction velocity 3.2x above 90-day average for CUST-0234.",
         "time": "3 hr ago", "read": True, "case_id": "CASE-003"},
        {"id": "ALT-005", "severity": "MEDIUM", "title": "Round-Number Transactions",
         "message": "6 consecutive round-number cash withdrawals detected.",
         "time": "5 hr ago", "read": True, "case_id": "CASE-001"},
        {"id": "ALT-006", "severity": "LOW", "title": "Address Mismatch",
         "message": "KYC address does not match transaction origination country.",
         "time": "1 day ago", "read": True, "case_id": "CASE-003"},
    ]

def _sample_audit_log():
    return [
        {"timestamp": "2024-01-25 09:14:32", "user": "analyst1", "action": "SAR_GENERATED",
         "case_id": "CASE-005", "details": "AI narrative generated for smurfing case"},
        {"timestamp": "2024-01-25 09:30:11", "user": "supervisor1", "action": "SAR_REVIEWED",
         "case_id": "CASE-005", "details": "Narrative reviewed and approved"},
        {"timestamp": "2024-01-24 14:22:05", "user": "analyst1", "action": "CASE_CREATED",
         "case_id": "CASE-005", "details": "New suspicious activity case created"},
        {"timestamp": "2024-01-23 11:05:47", "user": "admin", "action": "USER_LOGIN",
         "case_id": "—", "details": "Admin login from 192.168.1.10"},
        {"timestamp": "2024-01-22 16:45:33", "user": "analyst1", "action": "SAR_GENERATED",
         "case_id": "CASE-004", "details": "PEP risk SAR narrative generated"},
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

SYSTEM_PROMPT = """You are a Regulator-Grade Financial Crime Compliance AI Engine.
Generate SAR draft narratives and complete machine-auditable reasoning records.
Follow FinCEN, FIU-IND, and FATF standards.

RULES:
- Use ONLY the structured case data provided. Do NOT fabricate data.
- Use regulator-safe language. Do NOT state criminal guilt.
- Base suspicion solely on financial behavior.

OUTPUT TWO SECTIONS EXACTLY:

SECTION A — SAR DRAFT NARRATIVE
## 1. Subject Information
## 2. Summary of Suspicious Activity
## 3. Detailed Transaction Pattern Analysis
## 4. Typology Mapping
## 5. Risk Scoring & Threshold Analysis
## 6. Data Completeness & Limitations
## 7. Conclusion

SECTION B — COMPLETE AUDIT TRAIL (STRICT JSON, no markdown fences):
{
  "case_id": "<case_id>",
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
  "model_limitations": "LLM-generated narrative requires human review.",
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
    from langchain.schema import SystemMessage, HumanMessage
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
            <div class="login-sub">Barclays AML Compliance Platform</div>
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
            <div style="font-size:0.7rem; color:#5c7a9e; letter-spacing:2px;">BARCLAYS AML</div>
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
            f"v2.0 | Barclays AML © 2024</div>",
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown("## 📊 Dashboard")
    st.markdown("**AML Compliance Overview**")
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
def page_generate_sar():
    st.markdown("## 🚀 Generate SAR Narrative")
    if not can_generate():
        st.warning("🔒 Read-only access: SAR generation requires ANALYST or ADMIN role.")
        return
    st.divider()

    # LLM config
    with st.expander("🔑 LLM Configuration", expanded=not bool(st.session_state.get("_api_key"))):
        provider = st.selectbox("Provider", ["Groq", "OpenAI"], key="provider")
        api_key  = st.text_input("API Key", type="password",
                                 placeholder="gsk_..." if st.session_state.get("provider","Groq")=="Groq" else "sk-...",
                                 key="_api_key")

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
            m1.metric("Total Value", f"₹{sum(t['amount'] for t in st.session_state.transactions):,.0f}")
            m2.metric("Flagged", sum(1 for t in st.session_state.transactions if t.get("is_flagged")))
            m3.metric("Countries", len(set(t.get("country","") for t in st.session_state.transactions if t.get("country"))))
            if st.button("🗑️ Clear All Transactions"):
                st.session_state.transactions = []
                st.rerun()

    with tab_rules:
        SAMPLE_RULES = {
            "STR001 – Cash threshold breach":      ("STR001","Cash transaction exceeds ₹10L threshold","Structuring",1000000),
            "LAY002 – Layering via offshore":      ("LAY002","Multiple offshore wire transfers within 72h","Layering",3),
            "SMRF003 – Smurfing pattern":          ("SMRF003","Multiple sub-threshold deposits detected","Smurfing",990000),
            "PEP004 – PEP high-risk transaction":  ("PEP004","Politically Exposed Person high-value txn","PEP Risk",500000),
            "VELOC005 – Velocity spike":           ("VELOC005","Transaction velocity 3x above 90-day avg","Velocity",3),
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
        warnings = []
        ak = st.session_state.get("_api_key","")
        if not ak: warnings.append("⚠️ No API key entered above.")
        if not st.session_state.transactions: warnings.append("⚠️ No transactions added.")
        if not st.session_state.rule_triggers: warnings.append("⚠️ No rule triggers added.")
        for w in warnings: st.warning(w)

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
                        "time": "just now", "read": False,
                        "case_id": case_dict["case_id"],
                    })
                    st.success("✅ SAR generated successfully!")
                except Exception as exc:
                    st.session_state.generation_error = str(exc)
                    st.error(f"Generation failed: {exc}")

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
                f"<div style='margin-top:6px; color:#cdd5e0;'>{a['message']}</div>"
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
        "<small>⚖️ **Disclaimer:** AI-assisted SAR drafts for compliance review only. "
        "All outputs require approval by a qualified compliance officer before submission.</small>",
        unsafe_allow_html=True,
    )
