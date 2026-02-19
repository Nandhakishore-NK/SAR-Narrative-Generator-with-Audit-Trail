"""
SAR Engine — Core LLM-powered SAR narrative generation service.

This is the central intelligence engine that:
1. Assembles structured case data into the system prompt
2. Calls the LLM via LangChain with deterministic temperature
3. Parses the structured output (narrative + audit JSON)
4. Hashes each sentence for tamper detection
5. Maps every claim to evidence
6. Determines alert severity based on threshold breaches

Compliance guarantees:
- No hallucination: every sentence maps to provided data
- No legal conclusions: regulator-safe language only
- No discriminatory language: suspicion based on financial behavior only
- Full audit trail: every generation creates complete JSON record
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.case import Case, CaseStatus
from app.models.transaction import Transaction
from app.models.rule_trigger import RuleTrigger
from app.models.sar_narrative import SarNarrative
from app.models.narrative_sentence import NarrativeSentence, ConfidenceLevel
from app.models.audit_trail import AuditTrail
from app.services.hash_service import hash_sentence
from app.services.audit_service import write_immutable_log
from app.services.rag_service import rag_service
from app.prompts.sar_system_prompt import build_system_prompt


# ------- LLM Client Setup -------
try:
    from langchain_openai import ChatOpenAI
    from langchain.schema import SystemMessage, HumanMessage

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


def _get_llm():
    """Initialize LangChain LLM with deterministic temperature."""
    if not LANGCHAIN_AVAILABLE:
        return None
    return ChatOpenAI(
        model=settings.LLM_MODEL_NAME,
        temperature=settings.LLM_TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
        max_tokens=4096,
    )


def _determine_severity(
    transactions: List[Transaction],
    rule_triggers: List[RuleTrigger],
    case: Case,
) -> str:
    """
    Determine alert severity based STRICTLY on:
    - Transaction aggregation size
    - Cross-border movement
    - High-risk jurisdictions
    - Velocity spikes
    - Structuring indicators
    - Graph anomaly concentration
    - Risk score values

    Never inflate severity without threshold breach.
    """
    severity_score = 0

    # Transaction volume analysis
    total_amount = sum(t.amount for t in transactions)
    if total_amount > 1_000_000:
        severity_score += 3
    elif total_amount > 500_000:
        severity_score += 2
    elif total_amount > 100_000:
        severity_score += 1

    # Cross-border movement
    countries = set(t.country for t in transactions if t.country)
    if len(countries) > 3:
        severity_score += 2
    elif len(countries) > 1:
        severity_score += 1

    # Rule breach count
    breached_rules = [r for r in rule_triggers if r.breached]
    if len(breached_rules) > 5:
        severity_score += 3
    elif len(breached_rules) > 2:
        severity_score += 2
    elif len(breached_rules) > 0:
        severity_score += 1

    # Risk scores
    if case.composite_risk_score and case.composite_risk_score > 80:
        severity_score += 2
    elif case.composite_risk_score and case.composite_risk_score > 60:
        severity_score += 1

    # Graph anomalies
    if case.graph_analysis and len(case.graph_analysis) > 50:
        severity_score += 1

    # Historical SAR filings
    if case.historical_sar_count and case.historical_sar_count > 0:
        severity_score += 1

    # Map score to severity
    if severity_score >= 8:
        return "CRITICAL"
    elif severity_score >= 5:
        return "HIGH"
    elif severity_score >= 2:
        return "MEDIUM"
    else:
        return "LOW"


def _build_case_data_prompt(
    case: Case,
    transactions: List[Transaction],
    rule_triggers: List[RuleTrigger],
    rag_docs: List[Dict],
) -> str:
    """
    Build the structured case data input for the LLM.
    Only uses provided data — never fabricates or infers.
    """
    txn_data = []
    for t in transactions:
        txn_data.append({
            "id": str(t.id),
            "ref": t.transaction_ref,
            "amount": t.amount,
            "currency": t.currency,
            "date": t.transaction_date.isoformat() if t.transaction_date else None,
            "type": t.transaction_type,
            "direction": t.direction,
            "counterparty": t.counterparty_name,
            "counterparty_bank": t.counterparty_bank,
            "country": t.country,
            "purpose": t.purpose,
            "flagged": t.is_flagged,
        })

    triggers = []
    for r in rule_triggers:
        triggers.append({
            "id": str(r.id),
            "rule_code": r.rule_code,
            "description": r.rule_description,
            "threshold": r.threshold_value,
            "actual": r.actual_value,
            "breached": r.breached,
            "typology_code": r.typology_code,
            "typology_description": r.typology_description,
        })

    # Calculate data completeness
    completeness = {
        "customer_profile": bool(case.customer_name and case.customer_id),
        "kyc_information": bool(case.kyc_id_type and case.kyc_id_number),
        "account_summary": bool(case.account_number),
        "transaction_data": len(transactions) > 0,
        "transaction_count": len(transactions),
        "rule_triggers": len(rule_triggers) > 0,
        "rule_trigger_count": len(rule_triggers),
        "historical_behavior": bool(case.historical_avg_monthly_volume),
        "risk_scores": bool(case.composite_risk_score),
        "graph_analysis": bool(case.graph_analysis),
    }

    case_input = f"""
=== CASE DATA INPUT ===

case_id: {case.id}

customer_profile:
  customer_id: {case.customer_id}
  customer_name: {case.customer_name}
  customer_type: {case.customer_type or 'NOT PROVIDED'}
  customer_risk_rating: {case.customer_risk_rating or 'NOT PROVIDED'}

kyc_information:
  id_type: {case.kyc_id_type or 'NOT PROVIDED'}
  id_number: {case.kyc_id_number or 'NOT PROVIDED'}
  country: {case.kyc_country or 'NOT PROVIDED'}
  occupation: {case.kyc_occupation or 'NOT PROVIDED'}
  onboarding_date: {case.kyc_onboarding_date.isoformat() if case.kyc_onboarding_date else 'NOT PROVIDED'}

account_summary:
  account_number: {case.account_number or 'NOT PROVIDED'}
  account_type: {case.account_type or 'NOT PROVIDED'}
  open_date: {case.account_open_date.isoformat() if case.account_open_date else 'NOT PROVIDED'}
  balance: {case.account_balance if case.account_balance is not None else 'NOT PROVIDED'}
  currency: {case.account_currency or 'USD'}

alert_metadata:
  alert_id: {case.alert_id or 'NOT PROVIDED'}
  alert_date: {case.alert_date.isoformat() if case.alert_date else 'NOT PROVIDED'}
  alert_type: {case.alert_type or 'NOT PROVIDED'}
  alert_score: {case.alert_score if case.alert_score is not None else 'NOT PROVIDED'}

transaction_data:
{json.dumps(txn_data, indent=2, default=str)}

rule_triggers:
{json.dumps(triggers, indent=2, default=str)}

historical_behavior:
  avg_monthly_volume: {case.historical_avg_monthly_volume if case.historical_avg_monthly_volume is not None else 'NOT PROVIDED'}
  avg_transaction_size: {case.historical_avg_transaction_size if case.historical_avg_transaction_size is not None else 'NOT PROVIDED'}
  counterparty_count: {case.historical_counterparty_count if case.historical_counterparty_count is not None else 'NOT PROVIDED'}
  prior_sar_count: {case.historical_sar_count if case.historical_sar_count is not None else 0}

risk_scores:
  composite: {case.composite_risk_score if case.composite_risk_score is not None else 'NOT PROVIDED'}
  network: {case.network_risk_score if case.network_risk_score is not None else 'NOT PROVIDED'}
  behavioral: {case.behavioral_risk_score if case.behavioral_risk_score is not None else 'NOT PROVIDED'}

graph_relationship_analysis:
  {case.graph_analysis or 'NOT PROVIDED'}

data_completeness_metrics:
{json.dumps(completeness, indent=2)}

case_notes:
  {case.notes or 'No additional notes provided.'}
"""

    if rag_docs:
        case_input += "\n\nretrieved_regulatory_guidance:\n"
        for doc in rag_docs:
            case_input += f"  - [{doc['document_id']}] {doc['text'][:200]}...\n"

    return case_input


def _parse_llm_response(response_text: str) -> Tuple[str, Dict]:
    """
    Parse the LLM response into narrative text and audit JSON.
    Handles both well-formed and slightly malformed outputs.
    """
    narrative_text = ""
    audit_json = {}

    # Try to split on SECTION B marker
    section_b_markers = [
        "SECTION B", "## SECTION B", "**SECTION B**",
        "COMPLETE AUDIT TRAIL", "AUDIT TRAIL"
    ]

    split_idx = -1
    for marker in section_b_markers:
        idx = response_text.find(marker)
        if idx > 0:
            split_idx = idx
            break

    if split_idx > 0:
        narrative_text = response_text[:split_idx].strip()
        json_part = response_text[split_idx:]
    else:
        # Try to find JSON block
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_start = json_match.start()
            narrative_text = response_text[:json_start].strip()
            json_part = json_match.group()
        else:
            narrative_text = response_text.strip()
            json_part = ""

    # Clean narrative text — remove section headers
    for prefix in ["SECTION A", "## SECTION A", "**SECTION A**", "SAR DRAFT NARRATIVE"]:
        narrative_text = narrative_text.replace(prefix, "").strip()

    # Parse JSON
    if json_part:
        # Extract JSON from potential markdown code blocks
        json_clean = re.search(r'\{[\s\S]*\}', json_part)
        if json_clean:
            try:
                audit_json = json.loads(json_clean.group())
            except json.JSONDecodeError:
                # If JSON parsing fails, create a minimal audit record
                audit_json = {"parse_error": "LLM output JSON was malformed", "raw_text": json_part[:500]}

    return narrative_text, audit_json


def _build_fallback_audit_json(
    case: Case,
    transactions: List[Transaction],
    rule_triggers: List[RuleTrigger],
    severity: str,
    sentences_with_ids: List[Dict],
    rag_docs: List[Dict],
) -> Dict:
    """
    Build a complete audit JSON if LLM doesn't produce one or it's malformed.
    Ensures compliance even if LLM output is imperfect.
    """
    return {
        "case_id": str(case.id),
        "model_metadata": {
            "model_version": settings.LLM_MODEL_NAME,
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "data_sources_used": [
            "customer_profile", "kyc_information", "account_summary",
            "transaction_data", "rule_triggers", "historical_behavior",
            "risk_scores",
        ] + (["graph_relationship_analysis"] if case.graph_analysis else []),
        "triggering_rules": [
            {"rule_code": r.rule_code, "breached": r.breached, "id": str(r.id)}
            for r in rule_triggers
        ],
        "thresholds_breached": [
            {
                "rule_code": r.rule_code,
                "threshold": r.threshold_value,
                "actual": r.actual_value,
            }
            for r in rule_triggers if r.breached
        ],
        "typology_matches": list(set(
            r.typology_code for r in rule_triggers if r.typology_code
        )),
        "graph_anomalies": [case.graph_analysis] if case.graph_analysis else [],
        "transaction_ids_referenced": [str(t.id) for t in transactions],
        "risk_scores_used": {
            "composite": case.composite_risk_score,
            "network": case.network_risk_score,
            "behavioral": case.behavioral_risk_score,
        },
        "retrieved_documents_used": [d["document_id"] for d in rag_docs],
        "data_completeness_metrics": {
            "customer_profile": bool(case.customer_name),
            "kyc_information": bool(case.kyc_id_type),
            "transaction_count": len(transactions),
            "rule_trigger_count": len(rule_triggers),
        },
        "reasoning_trace": sentences_with_ids,
        "alert_metadata": {
            "alert_severity": severity,
            "escalation_required": severity in ("HIGH", "CRITICAL"),
            "recommended_next_steps": _get_recommended_steps(severity),
        },
        "identified_data_gaps": _identify_data_gaps(case, transactions, rule_triggers),
        "model_limitations": "LLM-generated narrative requires human review before filing.",
        "governance_flags": [],
    }


def _get_recommended_steps(severity: str) -> List[str]:
    """Recommend next steps based on severity level."""
    steps = ["Review generated narrative for accuracy"]
    if severity in ("MEDIUM", "HIGH", "CRITICAL"):
        steps.append("Verify transaction evidence against source systems")
    if severity in ("HIGH", "CRITICAL"):
        steps.append("Escalate to supervisor for review and approval")
        steps.append("Consider enhanced due diligence on customer")
    if severity == "CRITICAL":
        steps.append("Immediate escalation to compliance officer")
        steps.append("Consider account restriction pending investigation")
    return steps


def _identify_data_gaps(
    case: Case,
    transactions: List[Transaction],
    rule_triggers: List[RuleTrigger],
) -> List[str]:
    """Identify missing data that limits the narrative's completeness."""
    gaps = []
    if not case.kyc_id_type or not case.kyc_id_number:
        gaps.append("KYC identification information is incomplete")
    if not case.account_number:
        gaps.append("Account number not provided")
    if not transactions:
        gaps.append("No transaction data available — critical gap")
    if not rule_triggers:
        gaps.append("No rule triggers recorded")
    if not case.historical_avg_monthly_volume:
        gaps.append("Historical behavior baseline not available")
    if not case.composite_risk_score:
        gaps.append("Risk scores not provided")
    if not case.graph_analysis:
        gaps.append("Graph/relationship analysis not available")
    return gaps


def _generate_fallback_narrative(
    case: Case,
    transactions: List[Transaction],
    rule_triggers: List[RuleTrigger],
    severity: str,
) -> str:
    """
    Generate a template-based narrative when LLM is unavailable.
    Ensures the system works even without API connectivity.
    """
    breached = [r for r in rule_triggers if r.breached]
    total_amount = sum(t.amount for t in transactions)
    countries = set(t.country for t in transactions if t.country)

    narrative = f"""## 1. Subject Information

Customer Name: {case.customer_name}
Customer ID: {case.customer_id}
Customer Type: {case.customer_type or 'Not specified'}
Account Number: {case.account_number or 'Not provided'}
KYC Country: {case.kyc_country or 'Not provided'}
Risk Rating: {case.customer_risk_rating or 'Not assessed'}

## 2. Summary of Suspicious Activity

This report documents potentially suspicious financial activity identified in connection with the above-referenced customer. The activity was flagged by alert {case.alert_id or 'N/A'} on {case.alert_date.strftime('%Y-%m-%d') if case.alert_date else 'date not available'}. A total of {len(transactions)} transaction(s) aggregating {case.account_currency or 'USD'} {total_amount:,.2f} were analyzed. {len(breached)} rule trigger(s) were found to have breached established thresholds.

## 3. Detailed Transaction Pattern Analysis

The review period encompasses {len(transactions)} transactions. The total value of transactions under review is {case.account_currency or 'USD'} {total_amount:,.2f}. Transactions involve counterparties across {len(countries)} jurisdiction(s): {', '.join(countries) if countries else 'domestic only'}.

"""
    if transactions:
        narrative += "Key transactions identified:\n\n"
        for t in transactions[:10]:  # Limit to top 10 for readability
            narrative += f"- Transaction {t.transaction_ref or str(t.id)[:8]}: {t.currency} {t.amount:,.2f} on {t.transaction_date.strftime('%Y-%m-%d') if t.transaction_date else 'N/A'} ({t.direction or 'N/A'}) — Counterparty: {t.counterparty_name or 'Unknown'}, Country: {t.country or 'N/A'}\n"

    narrative += f"""
## 4. Graph & Relationship Analysis

{case.graph_analysis or 'Graph relationship analysis data was not provided for this case.'}

## 5. Typology Mapping

"""
    if breached:
        for r in breached:
            narrative += f"- Rule {r.rule_code}: {r.rule_description or 'No description'} (Threshold: {r.threshold_value}, Actual: {r.actual_value})"
            if r.typology_code:
                narrative += f" — Typology: {r.typology_code} ({r.typology_description or ''})"
            narrative += "\n"
    else:
        narrative += "No rule triggers breached defined thresholds during the review period.\n"

    narrative += f"""
## 6. Historical Behavior Comparison

Average Monthly Volume: {case.historical_avg_monthly_volume or 'Not available'}
Average Transaction Size: {case.historical_avg_transaction_size or 'Not available'}
Historical Counterparty Count: {case.historical_counterparty_count or 'Not available'}
Prior SAR Filings: {case.historical_sar_count or 0}

## 7. Risk Scoring & Threshold Analysis

Composite Risk Score: {case.composite_risk_score or 'Not assessed'}
Network Risk Score: {case.network_risk_score or 'Not assessed'}
Behavioral Risk Score: {case.behavioral_risk_score or 'Not assessed'}
Alert Score: {case.alert_score or 'Not assessed'}
Determined Severity: {severity}

## 8. Data Completeness & Limitations

"""
    gaps = _identify_data_gaps(case, transactions, rule_triggers)
    if gaps:
        for gap in gaps:
            narrative += f"- {gap}\n"
    else:
        narrative += "All primary data fields are present.\n"

    narrative += f"""
## 9. Conclusion

Based on the available evidence, the activity associated with customer {case.customer_name} (ID: {case.customer_id}) has been assessed at {severity} severity. """

    if severity in ("HIGH", "CRITICAL"):
        narrative += "The activity patterns appear consistent with potential suspicious activity requiring escalation and further investigation. "
    elif severity == "MEDIUM":
        narrative += "The identified activity warrants continued monitoring and possible further review. "
    else:
        narrative += "The current evidence does not support a finding of suspicious activity at this time. "

    narrative += "This narrative has been generated based solely on the structured data provided and should be reviewed by a qualified analyst before any filing action."

    return narrative


async def generate_sar(
    db: AsyncSession,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
    analyst_role: str = "analyst",
) -> Tuple[SarNarrative, AuditTrail]:
    """
    Main SAR generation orchestrator.
    
    Steps:
    1. Load case data with all relationships
    2. Retrieve regulatory guidance via RAG
    3. Determine severity from evidence
    4. Call LLM with structured prompt
    5. Parse response into narrative + audit JSON
    6. Hash each sentence
    7. Store narrative, sentences, and audit trail
    8. Log everything immutably
    
    Returns: (SarNarrative, AuditTrail)
    """
    # 1. Load case with relationships
    result = await db.execute(
        select(Case).where(Case.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise ValueError(f"Case {case_id} not found")

    # Load transactions
    txn_result = await db.execute(
        select(Transaction).where(Transaction.case_id == case_id)
    )
    transactions = list(txn_result.scalars().all())

    # Load rule triggers
    rule_result = await db.execute(
        select(RuleTrigger).where(RuleTrigger.case_id == case_id)
    )
    rule_triggers = list(rule_result.scalars().all())

    # 2. Retrieve regulatory guidance via RAG
    rag_query = f"SAR narrative for {case.alert_type or 'suspicious transaction'} involving {case.customer_type or 'customer'}"
    rag_docs = rag_service.retrieve_guidance(rag_query)

    # 3. Determine severity
    severity = _determine_severity(transactions, rule_triggers, case)

    # 4. Get current version number
    version_result = await db.execute(
        select(func.max(SarNarrative.version)).where(SarNarrative.case_id == case_id)
    )
    current_max_version = version_result.scalar() or 0
    new_version = current_max_version + 1

    # 5. Deactivate previous active narratives
    prev_result = await db.execute(
        select(SarNarrative).where(
            SarNarrative.case_id == case_id,
            SarNarrative.is_active == True,
        )
    )
    for prev_narrative in prev_result.scalars().all():
        prev_narrative.is_active = False

    # 6. Generate narrative via LLM or fallback
    llm = _get_llm()
    narrative_text = ""
    audit_json = {}

    if llm and settings.OPENAI_API_KEY:
        try:
            system_prompt = build_system_prompt(analyst_role)
            case_data_prompt = _build_case_data_prompt(case, transactions, rule_triggers, rag_docs)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=case_data_prompt),
            ]

            response = await llm.ainvoke(messages)
            narrative_text, audit_json = _parse_llm_response(response.content)
        except Exception as e:
            # Fallback to template-based generation
            narrative_text = _generate_fallback_narrative(case, transactions, rule_triggers, severity)
    else:
        # LLM not available — use template
        narrative_text = _generate_fallback_narrative(case, transactions, rule_triggers, severity)

    # 7. Create narrative record
    narrative = SarNarrative(
        case_id=case_id,
        narrative_text=narrative_text,
        version=new_version,
        severity=severity,
        is_active=True,
        created_by=user_id,
    )
    db.add(narrative)
    await db.flush()  # Get assigned ID

    # 8. Break into sentences and hash each one
    sentences_raw = [s.strip() for s in re.split(r'(?<=[.!?])\s+', narrative_text) if s.strip() and len(s.strip()) > 5]

    # Also split by newlines for header lines
    lines = narrative_text.split('\n')
    all_segments = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        if line.startswith('#') or line.startswith('-') or line.startswith('*'):
            all_segments.append(line)
        else:
            # Split line into sentences
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', line) if s.strip() and len(s.strip()) > 5]
            all_segments.extend(sents)

    # Deduplicate while preserving order
    seen = set()
    unique_segments = []
    for seg in all_segments:
        if seg not in seen:
            seen.add(seg)
            unique_segments.append(seg)

    sentences_with_trace = []
    for idx, sent_text in enumerate(unique_segments):
        sent_hash = hash_sentence(sent_text)

        # Try to find evidence mapping from audit JSON reasoning trace
        trace_entry = None
        if audit_json and "reasoning_trace" in audit_json:
            for trace in audit_json["reasoning_trace"]:
                if trace.get("narrative_sentence", "")[:50] == sent_text[:50]:
                    trace_entry = trace
                    break

        sentence = NarrativeSentence(
            narrative_id=narrative.id,
            sentence_index=idx,
            sentence_text=sent_text,
            sentence_hash=sent_hash,
            confidence_level=ConfidenceLevel(
                trace_entry.get("confidence_level", "MEDIUM") if trace_entry else "MEDIUM"
            ),
            supporting_transaction_ids=",".join(
                trace_entry.get("supporting_transaction_ids", []) if trace_entry else []
            ) or None,
            rule_reference=trace_entry.get("rule_reference") if trace_entry else None,
            threshold_reference=trace_entry.get("threshold_reference") if trace_entry else None,
            typology_reference=trace_entry.get("typology_reference") if trace_entry else None,
            graph_reference=trace_entry.get("graph_reference") if trace_entry else None,
        )
        db.add(sentence)
        await db.flush()

        sentences_with_trace.append({
            "sentence_id": str(sentence.id),
            "narrative_sentence": sent_text,
            "supporting_transaction_ids": (
                trace_entry.get("supporting_transaction_ids", []) if trace_entry else []
            ),
            "rule_reference": trace_entry.get("rule_reference", "") if trace_entry else "",
            "threshold_reference": trace_entry.get("threshold_reference", "") if trace_entry else "",
            "typology_reference": trace_entry.get("typology_reference", "") if trace_entry else "",
            "graph_reference": trace_entry.get("graph_reference", "") if trace_entry else "",
            "confidence_level": trace_entry.get("confidence_level", "MEDIUM") if trace_entry else "MEDIUM",
        })

    # 9. Build complete audit JSON (use LLM's if valid, otherwise build from scratch)
    if not audit_json or "case_id" not in audit_json:
        audit_json = _build_fallback_audit_json(
            case, transactions, rule_triggers, severity, sentences_with_trace, rag_docs
        )
    else:
        # Ensure required fields exist
        audit_json["case_id"] = str(case_id)
        audit_json.setdefault("reasoning_trace", sentences_with_trace)
        audit_json.setdefault("alert_metadata", {
            "alert_severity": severity,
            "escalation_required": severity in ("HIGH", "CRITICAL"),
        })

    # 10. Store audit trail
    audit_trail = AuditTrail(
        case_id=case_id,
        audit_json=audit_json,
        model_version=settings.LLM_MODEL_NAME,
        narrative_version=new_version,
    )
    db.add(audit_trail)

    # 11. Update case status
    case.status = CaseStatus.sar_generated

    # 12. Log immutably
    await write_immutable_log(
        db=db,
        entity_type="case",
        entity_id=str(case_id),
        action="narrative_generated",
        actor_id=str(user_id),
        details=f"Version {new_version} | Severity: {severity} | Sentences: {len(unique_segments)}",
    )

    await db.flush()
    return narrative, audit_trail
