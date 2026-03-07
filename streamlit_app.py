"""
SAR Narrative Generator with Audit Trail
=========================================
Streamlit-based frontend for generating FinCEN / FIU-IND compliant
Suspicious Activity Report (SAR) narratives powered by an LLM.

Features
--------
- Manual case, transaction & rule-trigger entry
- Groq (llama-3.3-70b-versatile) or OpenAI generation
- Structured Section A narrative + Section B JSON audit trail
- SHA-256 sentence-level hash integrity
- Downloadable audit record
- Full session-history of all generated SARs
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page config (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SAR Narrative Generator",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        .main-title { font-size: 2rem; font-weight: 700; color: #1e88e5; }
        .section-header { font-size: 1.1rem; font-weight: 600; color: #e8eaf6; background:#1565c0;
                          padding:6px 12px; border-radius:6px; margin-bottom:8px; }
        .confidence-HIGH   { color: #4caf50; font-weight: bold; }
        .confidence-MEDIUM { color: #ff9800; font-weight: bold; }
        .confidence-LOW    { color: #f44336; font-weight: bold; }
        .hash-box { font-family:monospace; font-size:0.75rem; color:#90caf9;
                    background:#0d1117; padding:4px 8px; border-radius:4px; }
        .severity-CRITICAL { background:#b71c1c; color:white; padding:4px 10px; border-radius:6px; font-weight:bold; }
        .severity-HIGH     { background:#e53935; color:white; padding:4px 10px; border-radius:6px; font-weight:bold; }
        .severity-MEDIUM   { background:#fb8c00; color:white; padding:4px 10px; border-radius:6px; font-weight:bold; }
        .severity-LOW      { background:#388e3c; color:white; padding:4px 10px; border-radius:6px; font-weight:bold; }
        .stTabs [data-baseweb="tab-list"] button { font-size: 0.95rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────────────────────
for key, default in {
    "transactions": [],
    "rule_triggers": [],
    "sar_history": [],          # list of generated SAR records
    "current_sar": None,
    "generation_error": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get_llm_client(api_key: str, provider: str):
    """Return a LangChain chat model or None."""
    try:
        if provider == "Groq":
            from langchain_groq import ChatGroq
            return ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                groq_api_key=api_key,
                max_tokens=4096,
            )
        else:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o",
                temperature=0.2,
                openai_api_key=api_key,
                max_tokens=4096,
            )
    except Exception as exc:
        return None, str(exc)


SYSTEM_PROMPT = """You are a Regulator-Grade Financial Crime Compliance AI Engine.

Your sole function is to generate Suspicious Activity Report (SAR) draft narratives
and a complete machine-auditable reasoning record.

You operate under regulatory standards aligned with FinCEN, FIU-IND, and FATF.

=====================================================
NON-NEGOTIABLE OPERATIONAL RULES
=====================================================

DATA BOUNDARY CONTROL:
- Use ONLY the structured case data provided.
- Do NOT fabricate transaction IDs, amounts, dates, or names.
- If data is marked "NOT PROVIDED", explicitly state the data gap.

NO HALLUCINATION POLICY:
Every material narrative claim MUST map to at least one of:
- A transaction ID from the provided transaction_data
- A rule trigger ID from the provided rule_triggers
- A breached threshold from the provided data

NO LEGAL CONCLUSIONS:
- Do NOT state criminal guilt or innocence.
- Use regulator-safe language: "Activity appears consistent with potential layering typology."

NO DISCRIMINATORY LANGUAGE:
- Suspicion must be based SOLELY on financial behavior.

=====================================================
REQUIRED OUTPUT STRUCTURE
=====================================================

You MUST output EXACTLY TWO SECTIONS:

-----------------------------------------------------
SECTION A — SAR DRAFT NARRATIVE
-----------------------------------------------------
## 1. Subject Information
## 2. Summary of Suspicious Activity
## 3. Detailed Transaction Pattern Analysis
## 4. Typology Mapping
## 5. Risk Scoring & Threshold Analysis
## 6. Data Completeness & Limitations
## 7. Conclusion

-----------------------------------------------------
SECTION B — COMPLETE AUDIT TRAIL (STRICT JSON)
-----------------------------------------------------

Output VALID machine-parseable JSON ONLY (no markdown code fences):

{
  "case_id": "<case_id>",
  "model_metadata": {
      "model_version": "llama-3.3-70b-versatile",
      "generation_timestamp": "<ISO-8601>"
  },
  "data_sources_used": [],
  "triggering_rules": [],
  "thresholds_breached": [],
  "typology_matches": [],
  "transaction_ids_referenced": [],
  "risk_scores_used": {},
  "data_completeness_metrics": {},
  "reasoning_trace": [
      {
         "sentence_id": "S001",
         "narrative_sentence": "exact sentence text",
         "supporting_transaction_ids": [],
         "rule_reference": "",
         "confidence_level": "LOW | MEDIUM | HIGH"
      }
  ],
  "alert_metadata": {
      "alert_severity": "LOW | MEDIUM | HIGH | CRITICAL",
      "escalation_required": true,
      "recommended_next_steps": []
  },
  "identified_data_gaps": [],
  "model_limitations": "LLM-generated narrative requires human review.",
  "governance_flags": []
}

Return ONLY Section A and Section B. No commentary outside those sections."""


def _build_case_prompt(case: dict, transactions: list, rule_triggers: list) -> str:
    return f"""
CASE DATA:
{json.dumps(case, indent=2, default=str)}

TRANSACTIONS ({len(transactions)} records):
{json.dumps(transactions, indent=2, default=str)}

RULE TRIGGERS ({len(rule_triggers)} records):
{json.dumps(rule_triggers, indent=2, default=str)}

Generate the SAR narrative and audit trail now.
"""


def _parse_sar_output(raw: str, case_id: str) -> dict:
    """
    Split LLM output into narrative text + audit JSON.
    Returns dict with keys: narrative, audit, sentences_with_hashes.
    """
    # Find Section B JSON block
    section_b_match = re.search(
        r"SECTION B.*?AUDIT TRAIL.*?\n([\s\S]*)", raw, re.IGNORECASE
    )
    audit_json = {}
    narrative = raw

    if section_b_match:
        raw_json_str = section_b_match.group(1).strip()
        # Strip any trailing markdown fences
        raw_json_str = re.sub(r"```[a-z]*", "", raw_json_str).strip().rstrip("`").strip()
        # Find first { and last }
        start = raw_json_str.find("{")
        end = raw_json_str.rfind("}") + 1
        if start != -1 and end > start:
            try:
                audit_json = json.loads(raw_json_str[start:end])
            except json.JSONDecodeError:
                audit_json = {"parse_error": "Could not decode audit JSON", "raw": raw_json_str[start:end][:500]}

        # Section A is everything before SECTION B
        sec_b_start = raw.upper().find("SECTION B")
        if sec_b_start != -1:
            narrative = raw[:sec_b_start].strip()

    # Hash each sentence in the narrative
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narrative) if len(s.strip()) > 20]
    sentences_with_hashes = [{"sentence": s, "hash": sha256(s)} for s in sentences]

    return {
        "case_id": case_id,
        "narrative": narrative,
        "audit": audit_json,
        "sentences_with_hashes": sentences_with_hashes,
        "severity": audit_json.get("alert_metadata", {}).get("alert_severity", "UNKNOWN"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_sar(case: dict, transactions: list, rule_triggers: list, api_key: str, provider: str):
    """Call the LLM and return parsed SAR dict."""
    from langchain.schema import SystemMessage, HumanMessage

    llm = _get_llm_client(api_key, provider)
    if llm is None:
        raise RuntimeError("Could not initialise LLM client. Check your API key and provider.")

    human_prompt = _build_case_prompt(case, transactions, rule_triggers)
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=human_prompt)]

    response = llm.invoke(messages)
    raw_output = response.content if hasattr(response, "content") else str(response)

    return _parse_sar_output(raw_output, case.get("case_id", str(uuid.uuid4())))


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/bank.png", width=60)
    st.markdown("## 🛡️ SAR Guardian")
    st.markdown("*Regulator-grade SAR narrative generation*")
    st.divider()

    st.markdown("### 🔑 LLM Configuration")
    provider = st.selectbox("Provider", ["Groq", "OpenAI"], index=0)
    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="gsk_..." if provider == "Groq" else "sk-...",
        help="Get a free Groq key at console.groq.com",
    )

    st.divider()
    st.markdown("### 📋 Session Summary")
    st.metric("Transactions entered", len(st.session_state.transactions))
    st.metric("Rule triggers entered", len(st.session_state.rule_triggers))
    st.metric("SARs generated", len(st.session_state.sar_history))

    if st.session_state.sar_history:
        st.divider()
        st.markdown("### 🕑 History")
        for i, rec in enumerate(reversed(st.session_state.sar_history[-5:])):
            sev = rec.get("severity", "?")
            ts = rec.get("generated_at", "")[:19].replace("T", " ")
            st.markdown(
                f"**{i+1}.** `{rec['case_id'][:8]}…`  \n"
                f"Severity: `{sev}` | {ts}"
            )

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🛡️ SAR Narrative Generator with Audit Trail</div>', unsafe_allow_html=True)
st.markdown(
    "Generate FinCEN / FIU-IND compliant SAR draft narratives with full machine-auditable reasoning. "
    "Every sentence is SHA-256 hashed for tamper detection."
)
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_case, tab_txn, tab_rules, tab_generate, tab_audit, tab_history = st.tabs(
    ["📁 Case Details", "💸 Transactions", "⚠️ Rule Triggers", "🚀 Generate SAR", "🔍 Audit Trail", "📜 History"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Case Details
# ══════════════════════════════════════════════════════════════════════════════
with tab_case:
    st.markdown('<div class="section-header">Customer & Case Information</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        case_id        = st.text_input("Case ID", value=f"CASE-{uuid.uuid4().hex[:8].upper()}", key="case_id_input")
        customer_id    = st.text_input("Customer ID", placeholder="CUST-001", key="cust_id")
        customer_name  = st.text_input("Customer Name", placeholder="John Doe", key="cust_name")
        customer_type  = st.selectbox("Customer Type", ["individual", "entity", "PEP", "correspondent_bank"], key="cust_type")
        risk_rating    = st.selectbox("Customer Risk Rating", ["LOW", "MEDIUM", "HIGH", "CRITICAL"], key="risk_rating")

    with col2:
        account_number = st.text_input("Account Number", placeholder="ACC-123456", key="acc_num")
        account_type   = st.selectbox("Account Type", ["savings", "current", "offshore", "correspondent"], key="acc_type")
        account_bal    = st.number_input("Account Balance (INR)", min_value=0.0, step=1000.0, key="acc_bal")
        alert_id       = st.text_input("Alert ID", placeholder="ALT-2024-001", key="alert_id")
        alert_type     = st.text_input("Alert Type", placeholder="e.g. Structuring, Layering", key="alert_type")
        alert_score    = st.slider("Alert Score (0–100)", 0, 100, 75, key="alert_score")

    st.markdown('<div class="section-header">KYC Information</div>', unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        kyc_id_type    = st.text_input("ID Type", placeholder="Passport / Aadhaar / PAN", key="kyc_id_type")
        kyc_id_number  = st.text_input("ID Number", placeholder="XXXX-XXXX", key="kyc_id_num")
        kyc_country    = st.text_input("Country of Origin", placeholder="India", key="kyc_country")
    with col4:
        kyc_occupation = st.text_input("Occupation", placeholder="Business Owner", key="kyc_occ")
        composite_risk = st.slider("Composite Risk Score (0–100)", 0, 100, 65, key="composite_risk")
        hist_sar_count = st.number_input("Prior SAR Filings", min_value=0, step=1, key="hist_sar")

    st.markdown('<div class="section-header">Narrative Analyst Notes</div>', unsafe_allow_html=True)
    analyst_notes = st.text_area(
        "Case notes / additional context for the LLM",
        placeholder="Describe any unusual patterns, relationship context, or investigation background…",
        height=120,
        key="analyst_notes",
    )

    # Build case dict on demand (stored in session on Generate click)
    def _build_case_dict():
        return {
            "case_id": st.session_state.case_id_input,
            "customer_id": st.session_state.cust_id,
            "customer_name": st.session_state.cust_name,
            "customer_type": st.session_state.cust_type,
            "customer_risk_rating": st.session_state.risk_rating,
            "account_number": st.session_state.acc_num,
            "account_type": st.session_state.acc_type,
            "account_balance": st.session_state.acc_bal,
            "alert_id": st.session_state.alert_id,
            "alert_type": st.session_state.alert_type,
            "alert_score": st.session_state.alert_score,
            "kyc_id_type": st.session_state.kyc_id_type,
            "kyc_id_number": st.session_state.kyc_id_num,
            "kyc_country": st.session_state.kyc_country,
            "kyc_occupation": st.session_state.kyc_occ,
            "composite_risk_score": st.session_state.composite_risk,
            "historical_sar_count": st.session_state.hist_sar,
            "analyst_notes": st.session_state.analyst_notes,
        }

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Transactions
# ══════════════════════════════════════════════════════════════════════════════
with tab_txn:
    st.markdown('<div class="section-header">Add Transactions</div>', unsafe_allow_html=True)

    with st.form("txn_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            txn_ref    = st.text_input("Transaction Ref", placeholder="TXN-001")
            txn_amount = st.number_input("Amount", min_value=0.0, step=500.0)
            txn_curr   = st.selectbox("Currency", ["INR", "USD", "EUR", "GBP", "AED", "SGD"])
        with col2:
            txn_date   = st.date_input("Transaction Date")
            txn_type   = st.selectbox("Type", ["wire", "cash", "ach", "swift", "upi", "rtgs", "neft", "crypto"])
            txn_dir    = st.selectbox("Direction", ["outbound", "inbound"])
        with col3:
            cpty_name  = st.text_input("Counterparty Name")
            cpty_bank  = st.text_input("Counterparty Bank")
            country    = st.text_input("Country", placeholder="e.g. UAE")
            is_flagged = st.checkbox("Flagged")
        purpose    = st.text_input("Purpose / Narration")

        add_txn = st.form_submit_button("➕ Add Transaction", use_container_width=True, type="primary")
        if add_txn:
            st.session_state.transactions.append({
                "id": str(uuid.uuid4()),
                "transaction_ref": txn_ref or f"TXN-{len(st.session_state.transactions)+1:03d}",
                "amount": txn_amount,
                "currency": txn_curr,
                "transaction_date": str(txn_date),
                "transaction_type": txn_type,
                "direction": txn_dir,
                "counterparty_name": cpty_name,
                "counterparty_bank": cpty_bank,
                "country": country,
                "purpose": purpose,
                "is_flagged": is_flagged,
            })
            st.success(f"Transaction added. Total: {len(st.session_state.transactions)}")

    if st.session_state.transactions:
        st.markdown('<div class="section-header">Entered Transactions</div>', unsafe_allow_html=True)
        import pandas as pd
        df = pd.DataFrame(st.session_state.transactions)
        display_cols = ["transaction_ref", "amount", "currency", "transaction_date",
                        "transaction_type", "direction", "counterparty_name", "country", "is_flagged"]
        st.dataframe(df[[c for c in display_cols if c in df.columns]], use_container_width=True)

        total = sum(t["amount"] for t in st.session_state.transactions)
        flagged = sum(1 for t in st.session_state.transactions if t.get("is_flagged"))
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Value", f"₹{total:,.0f}")
        m2.metric("Flagged Transactions", flagged)
        m3.metric("Countries Involved", len(set(t.get("country","") for t in st.session_state.transactions if t.get("country"))))

        if st.button("🗑️ Clear All Transactions"):
            st.session_state.transactions = []
            st.rerun()
    else:
        st.info("No transactions added yet. Use the form above to add transactions.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Rule Triggers
# ══════════════════════════════════════════════════════════════════════════════
with tab_rules:
    st.markdown('<div class="section-header">Add Rule Triggers</div>', unsafe_allow_html=True)

    SAMPLE_RULES = {
        "STR001 – Cash threshold breach": ("STR001", "Cash transaction exceeds ₹10L threshold", "Structuring", 1000000),
        "LAY002 – Layering via offshore": ("LAY002", "Multiple offshore wire transfers within 72 hours", "Layering", 3),
        "SMRF003 – Smurfing pattern": ("SMRF003", "Multiple sub-threshold deposits structuring detection", "Smurfing", 990000),
        "PEP004 – PEP high-risk transaction": ("PEP004", "Politically Exposed Person high-value transaction", "PEP Risk", 500000),
        "VELOC005 – Velocity spike": ("VELOC005", "Transaction velocity 3x above 90-day average", "Velocity", 3),
        "CUSTOM – Enter manually": None,
    }

    preset = st.selectbox("Quick-fill from common rules", list(SAMPLE_RULES.keys()))

    with st.form("rule_form", clear_on_submit=True):
        prefill = SAMPLE_RULES.get(preset)
        col1, col2 = st.columns(2)
        with col1:
            rule_code  = st.text_input("Rule Code", value=prefill[0] if prefill else "")
            rule_desc  = st.text_input("Rule Description", value=prefill[1] if prefill else "")
            typology   = st.text_input("Typology", value=prefill[2] if prefill else "")
        with col2:
            threshold  = st.number_input("Threshold Value", value=float(prefill[3]) if prefill else 0.0)
            actual_val = st.number_input("Actual Value Observed", min_value=0.0, step=1.0)
            breached   = st.checkbox("Threshold Breached", value=True)

        add_rule = st.form_submit_button("➕ Add Rule Trigger", use_container_width=True, type="primary")
        if add_rule:
            st.session_state.rule_triggers.append({
                "id": str(uuid.uuid4()),
                "rule_code": rule_code,
                "rule_description": rule_desc,
                "typology_code": typology,
                "threshold_value": threshold,
                "actual_value": actual_val,
                "breached": breached,
            })
            st.success(f"Rule trigger added. Total: {len(st.session_state.rule_triggers)}")

    if st.session_state.rule_triggers:
        st.markdown('<div class="section-header">Entered Rule Triggers</div>', unsafe_allow_html=True)
        import pandas as pd
        df_r = pd.DataFrame(st.session_state.rule_triggers)
        st.dataframe(df_r[["rule_code", "rule_description", "typology_code",
                            "threshold_value", "actual_value", "breached"]],
                     use_container_width=True)

        if st.button("🗑️ Clear All Rules"):
            st.session_state.rule_triggers = []
            st.rerun()
    else:
        st.info("No rule triggers added yet.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Generate SAR
# ══════════════════════════════════════════════════════════════════════════════
with tab_generate:
    st.markdown('<div class="section-header">Generate SAR Narrative</div>', unsafe_allow_html=True)

    # Pre-flight checks
    warnings = []
    if not api_key:
        warnings.append("⚠️ No API key entered in the sidebar.")
    if not st.session_state.transactions:
        warnings.append("⚠️ No transactions added (Tab: Transactions).")
    if not st.session_state.rule_triggers:
        warnings.append("⚠️ No rule triggers added (Tab: Rule Triggers).")

    for w in warnings:
        st.warning(w)

    col_gen1, col_gen2 = st.columns([3, 1])
    with col_gen1:
        st.markdown(
            f"Ready to generate SAR for **{st.session_state.get('cust_name', '(unnamed)')}** "
            f"| Transactions: **{len(st.session_state.transactions)}** "
            f"| Rules breached: **{sum(1 for r in st.session_state.rule_triggers if r.get('breached'))}**"
        )
    with col_gen2:
        generate_btn = st.button(
            "🚀 Generate SAR",
            type="primary",
            use_container_width=True,
            disabled=bool(not api_key),
        )

    if generate_btn:
        if not api_key:
            st.error("Please enter your API key in the sidebar.")
        else:
            case_dict = _build_case_dict()

            with st.spinner("🔄 Calling LLM… this may take 15–30 seconds"):
                try:
                    result = generate_sar(
                        case_dict,
                        st.session_state.transactions,
                        st.session_state.rule_triggers,
                        api_key,
                        provider,
                    )
                    st.session_state.current_sar = result
                    st.session_state.sar_history.append(result)
                    st.session_state.generation_error = None
                    st.success("✅ SAR narrative generated successfully!")
                except Exception as exc:
                    st.session_state.generation_error = str(exc)
                    st.error(f"Generation failed: {exc}")

    if st.session_state.generation_error:
        st.error(st.session_state.generation_error)

    if st.session_state.current_sar:
        sar = st.session_state.current_sar
        sev = sar.get("severity", "UNKNOWN")

        st.divider()
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.markdown(f'**Alert Severity:** <span class="severity-{sev}">{sev}</span>', unsafe_allow_html=True)
        col_s2.metric("Sentences", len(sar.get("sentences_with_hashes", [])))
        col_s3.metric("Generated At", sar.get("generated_at", "")[:19].replace("T", " "))

        st.markdown('<div class="section-header">📄 Section A — SAR Draft Narrative</div>', unsafe_allow_html=True)
        st.markdown(sar["narrative"])

        st.divider()
        st.markdown('<div class="section-header">🔒 Sentence-Level SHA-256 Hashes</div>', unsafe_allow_html=True)
        for entry in sar.get("sentences_with_hashes", []):
            with st.expander(entry["sentence"][:100] + ("…" if len(entry["sentence"]) > 100 else ""), expanded=False):
                st.markdown(f'<div class="hash-box">{entry["hash"]}</div>', unsafe_allow_html=True)

        # Recommended next steps
        next_steps = sar.get("audit", {}).get("alert_metadata", {}).get("recommended_next_steps", [])
        if next_steps:
            st.divider()
            st.markdown('<div class="section-header">✅ Recommended Next Steps</div>', unsafe_allow_html=True)
            for step in next_steps:
                st.markdown(f"- {step}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Audit Trail
# ══════════════════════════════════════════════════════════════════════════════
with tab_audit:
    st.markdown('<div class="section-header">🔍 Machine-Auditable Reasoning Trace</div>', unsafe_allow_html=True)

    if not st.session_state.current_sar:
        st.info("Generate a SAR first (Tab: Generate SAR) to view the audit trail.")
    else:
        sar = st.session_state.current_sar
        audit = sar.get("audit", {})

        if "parse_error" in audit:
            st.warning("Audit JSON parse error. Showing raw output.")
            st.code(audit.get("raw", ""), language="json")
        else:
            # Summary metrics
            reasoning_trace = audit.get("reasoning_trace", [])
            high_conf  = sum(1 for r in reasoning_trace if r.get("confidence_level") == "HIGH")
            med_conf   = sum(1 for r in reasoning_trace if r.get("confidence_level") == "MEDIUM")
            low_conf   = sum(1 for r in reasoning_trace if r.get("confidence_level") == "LOW")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Sentences Traced", len(reasoning_trace))
            m2.metric("🟢 HIGH confidence", high_conf)
            m3.metric("🟡 MEDIUM confidence", med_conf)
            m4.metric("🔴 LOW confidence", low_conf)

            # Reasoning trace table
            if reasoning_trace:
                st.markdown('<div class="section-header">Sentence-Level Reasoning Trace</div>', unsafe_allow_html=True)
                import pandas as pd
                trace_df = pd.DataFrame(reasoning_trace)
                conf_col = "confidence_level"
                if conf_col in trace_df.columns:
                    # Colour-code
                    def _style_conf(val):
                        colours = {"HIGH": "#1b5e20", "MEDIUM": "#e65100", "LOW": "#b71c1c"}
                        return f"background-color: {colours.get(val, '#333')}"
                    st.dataframe(
                        trace_df[["sentence_id", "narrative_sentence", "supporting_transaction_ids",
                                  "rule_reference", "confidence_level"]] if all(
                            c in trace_df.columns for c in ["sentence_id","narrative_sentence","supporting_transaction_ids","rule_reference","confidence_level"]
                        ) else trace_df,
                        use_container_width=True,
                        height=350,
                    )

            # Data completeness
            completeness = audit.get("data_completeness_metrics", {})
            if completeness:
                st.markdown('<div class="section-header">Data Completeness Metrics</div>', unsafe_allow_html=True)
                st.json(completeness)

            # Governance flags
            gov_flags = audit.get("governance_flags", [])
            if gov_flags:
                st.markdown('<div class="section-header">⚑ Governance Flags</div>', unsafe_allow_html=True)
                for flag in gov_flags:
                    st.warning(flag)

            # Data gaps
            gaps = audit.get("identified_data_gaps", [])
            if gaps:
                st.markdown('<div class="section-header">⚠️ Identified Data Gaps</div>', unsafe_allow_html=True)
                for gap in gaps:
                    st.info(f"• {gap}")

            # Full JSON
            st.markdown('<div class="section-header">📦 Full Audit JSON</div>', unsafe_allow_html=True)
            st.json(audit)

        # Download
        st.divider()
        audit_str = json.dumps(
            {"narrative_hashes": sar.get("sentences_with_hashes", []), "audit": audit},
            indent=2, default=str,
        )
        st.download_button(
            "⬇️ Download Full Audit Record (JSON)",
            data=audit_str,
            file_name=f"SAR_audit_{sar['case_id']}_{sar['generated_at'][:10]}.json",
            mime="application/json",
            use_container_width=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — History
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown('<div class="section-header">📜 SAR Generation History (this session)</div>', unsafe_allow_html=True)

    if not st.session_state.sar_history:
        st.info("No SARs generated yet in this session.")
    else:
        for i, rec in enumerate(reversed(st.session_state.sar_history)):
            sev = rec.get("severity", "UNKNOWN")
            with st.expander(
                f"SAR #{len(st.session_state.sar_history) - i} | Case: {rec['case_id']} | "
                f"Severity: {sev} | {rec.get('generated_at','')[:19].replace('T',' ')}",
                expanded=(i == 0),
            ):
                st.markdown(rec["narrative"])
                audit_dl = json.dumps(rec.get("audit", {}), indent=2, default=str)
                st.download_button(
                    "⬇️ Download Audit JSON",
                    data=audit_dl,
                    file_name=f"SAR_audit_{rec['case_id']}.json",
                    mime="application/json",
                    key=f"dl_{i}",
                )

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<small>⚖️ **Disclaimer:** This tool generates AI-assisted SAR draft narratives for compliance review purposes only. "
    "All outputs must be reviewed and approved by a qualified compliance officer before submission. "
    "No legal conclusions are intended or implied.</small>",
    unsafe_allow_html=True,
)
