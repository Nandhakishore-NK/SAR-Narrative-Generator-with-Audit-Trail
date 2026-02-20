"""
SAR Narrative Generator Service
Uses LangChain with configurable LLM backends.
Supports full audit trail via LangChain callbacks.
"""
import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.config import settings
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert AML (Anti-Money Laundering) Compliance Analyst at a major UK bank, 
specialised in drafting Suspicious Activity Reports (SARs) for submission to the National Crime Agency (NCA).

YOUR ROLE AND MANDATE:
- Generate professional, regulator-ready SAR narratives based on transaction alerts and customer data
- Follow JMLSG guidance, POCA 2002 requirements, and FCA SYSC AML obligations
- Be objective, factual, and evidence-based — never speculative without supporting data
- Structure narratives using the 5W1H framework: Who, What, When, Where, Why, How

CRITICAL ETHICAL GUIDELINES (MANDATORY):
- You MUST be completely unbiased. Do not discriminate based on race, nationality, religion, 
  gender, age, or any protected characteristic
- Suspicion must be based SOLELY on transactional behavior, financial patterns, and legitimate 
  risk indicators — NEVER on personal characteristics
- Always assume innocence unless financial evidence clearly indicates suspicious activity
- If data is insufficient to justify suspicion, state this clearly
- Limit your analysis strictly to AML/financial crime — do not comment on unrelated matters

HOSTING ENVIRONMENT AWARENESS:
- On-premises: Emphasise data residency compliance, local record-keeping requirements
- Cloud: Note data sovereignty, encryption-at-rest, and cross-border data considerations
- Multi-cloud: Highlight consistent audit trail across environments

OUTPUT STRUCTURE - Always follow this exact format:
1. EXECUTIVE SUMMARY (2-3 sentences)
2. SUBJECT INFORMATION (customer & account details)
3. DESCRIPTION OF SUSPICIOUS ACTIVITY (detailed transaction narrative)
4. TIMELINE OF EVENTS (chronological list)
5. COUNTERPARTY ANALYSIS (who sent/received funds)
6. TYPOLOGY MATCH (which ML typology this matches)
7. REGULATORY BASIS FOR FILING (which laws/regulations apply)
8. CONCLUSION AND RECOMMENDATION

DOMAIN BOUNDARIES:
- Only analyse data provided in the context
- Do not infer or fabricate data not present in the input
- Keep customer, transaction, and fraud data strictly separated
- Do not cross-reference data from different domains without explicit linkage"""


NARRATIVE_PROMPT_TEMPLATE = """
## CASE CONTEXT

### Customer KYC Profile:
{customer_data}

### Transaction Alert Details:
{alert_data}

### Transaction Data:
{transaction_data}

### Risk Indicators Identified:
{risk_indicators}

### Hosting Environment:
{hosting_environment}

---

## RETRIEVED REGULATORY CONTEXT

### Relevant SAR Templates:
{sar_templates}

### Applicable Regulatory Guidelines:
{regulatory_guidelines}

---

## TASK

Based on the above data, generate a complete, professional SAR narrative report that:
1. Follows the mandatory output structure above
2. Uses specific figures, dates, and account references from the data provided
3. Matches the activity to appropriate money laundering typologies
4. Provides clear reasoning for WHY each data point contributes to suspicion
5. Is objective, factual, and defensible to regulators
6. Notes which data sources were used for each conclusion

At the END of the narrative, include an AUDIT REASONING SECTION formatted as:

### AUDIT TRAIL - REASONING LOG
DATA SOURCES USED:
- [List each data point used and why it was relevant]

RULES/TYPOLOGIES MATCHED:
- [List each rule or typology matched with the specific evidence]

CONFIDENCE ASSESSMENT:
- Overall suspicion confidence: [LOW/MEDIUM/HIGH/CRITICAL]
- Key factors driving the assessment: [List top 3-5 factors]

LIMITATIONS AND CAVEATS:
- [Note any data gaps, assumptions made, or limitations in the analysis]
"""


@dataclass
class GenerationResult:
    narrative: str
    audit_trail: Dict[str, Any]
    rag_sources: Dict[str, List]
    model_used: str
    prompt_hash: str
    generation_time_seconds: float
    tokens_used: Optional[int] = None
    confidence_level: str = "MEDIUM"
    typologies_matched: List[str] = field(default_factory=list)
    data_sources_used: List[str] = field(default_factory=list)
    rules_matched: List[str] = field(default_factory=list)
    error: Optional[str] = None


class SARGenerator:
    def __init__(self):
        self.llm = None
        self._model_name = ""

    def _get_llm(self):
        """Initialize the LLM based on configured provider."""
        if self.llm:
            return self.llm
        provider = settings.LLM_PROVIDER.lower()
        try:
            if provider == "openai":
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0.1,
                    max_tokens=settings.MAX_TOKENS_PER_NARRATIVE
                )
                self._model_name = settings.OPENAI_MODEL
            elif provider == "azure":
                from langchain_openai import AzureChatOpenAI
                self.llm = AzureChatOpenAI(
                    azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version="2024-02-01",
                    temperature=0.1,
                    max_tokens=settings.MAX_TOKENS_PER_NARRATIVE
                )
                self._model_name = f"azure:{settings.AZURE_OPENAI_DEPLOYMENT}"
            elif provider == "ollama" or provider == "local":
                from langchain_community.chat_models import ChatOllama
                self.llm = ChatOllama(
                    model=settings.OLLAMA_MODEL,
                    base_url=settings.OLLAMA_BASE_URL,
                    temperature=0.1
                )
                self._model_name = f"ollama:{settings.OLLAMA_MODEL}"
            elif provider == "groq":
                from langchain_groq import ChatGroq
                self.llm = ChatGroq(
                    model=settings.GROQ_MODEL,
                    api_key=settings.GROQ_API_KEY,
                    temperature=0.1,
                    max_tokens=settings.MAX_TOKENS_PER_NARRATIVE
                )
                self._model_name = f"groq:{settings.GROQ_MODEL}"
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
            return self.llm
        except Exception as e:
            logger.error(f"LLM initialization failed: {e}")
            raise

    def _build_prompt(
        self,
        customer_data: Dict,
        alert_data: Dict,
        transaction_data: List[Dict],
        rag_context: Dict,
        hosting_environment: str = "on-premises"
    ) -> str:
        """Build the full prompt for SAR generation."""
        risk_indicators = self._extract_risk_indicators(customer_data, alert_data, transaction_data)
        template_text = "\n\n---\n\n".join([
            f"Template: {t['metadata'].get('title', 'N/A')}\n{t['content'][:1500]}"
            for t in rag_context.get("templates", [])
        ]) or "No specific templates retrieved."
        regulation_text = "\n\n---\n\n".join([
            f"Regulation: {r['metadata'].get('title', 'N/A')}\n{r['content'][:1500]}"
            for r in rag_context.get("regulations", [])
        ]) or "No specific regulations retrieved."
        return NARRATIVE_PROMPT_TEMPLATE.format(
            customer_data=json.dumps(customer_data, indent=2, default=str),
            alert_data=json.dumps(alert_data, indent=2, default=str),
            transaction_data=json.dumps(transaction_data[:20], indent=2, default=str),
            risk_indicators=json.dumps(risk_indicators, indent=2),
            hosting_environment=hosting_environment,
            sar_templates=template_text,
            regulatory_guidelines=regulation_text
        )

    def _extract_risk_indicators(
        self, customer: Dict, alert: Dict, transactions: List[Dict]
    ) -> List[str]:
        """Automatically extract risk indicators from data."""
        indicators = []
        total_amount = alert.get("total_amount", 0)
        tx_count = alert.get("transaction_count", 0)
        if total_amount > 10000:
            indicators.append(f"HIGH VALUE: Total transactions of £{total_amount:,.2f} exceed £10,000 threshold")
        if tx_count > 10:
            indicators.append(f"HIGH FREQUENCY: {tx_count} transactions detected in monitoring window")
        if customer.get("pep_status"):
            indicators.append("PEP CUSTOMER: Subject is a Politically Exposed Person")
        if customer.get("risk_rating") in ["HIGH", "VERY HIGH"]:
            indicators.append(f"HIGH RISK CUSTOMER: Customer holds {customer.get('risk_rating')} risk rating")
        jurisdictions = alert.get("jurisdictions_involved", [])
        high_risk_j = [j for j in jurisdictions if j in ["Iran", "North Korea", "Syria", "Russia", "Afghanistan", "Myanmar"]]
        if high_risk_j:
            indicators.append(f"HIGH RISK JURISDICTION: Transactions linked to {', '.join(high_risk_j)}")
        if transactions:
            amounts = [t.get("amount", 0) for t in transactions]
            amounts_near_threshold = [a for a in amounts if 8000 <= a <= 9999]
            if amounts_near_threshold:
                indicators.append(f"STRUCTURING SUSPECTED: {len(amounts_near_threshold)} transactions near but below £10,000 reporting threshold")
        if alert.get("alert_type", "").upper() in ["RAPID_MOVEMENT", "ROUND_TRIP", "PASS_THROUGH"]:
            indicators.append("PASS-THROUGH PATTERN: Rapid in-out transaction pattern detected")
        annual_income = customer.get("annual_income", 1)
        if annual_income and total_amount > (annual_income * 2):
            indicators.append(f"INCOME DISPARITY: Transaction volume (£{total_amount:,.0f}) exceeds 2x stated annual income (£{annual_income:,.0f})")
        counterparties = alert.get("counterparties", [])
        if isinstance(counterparties, list) and len(counterparties) > 10:
            indicators.append(f"MULTIPLE COUNTERPARTIES: {len(counterparties)} distinct counterparties involved")
        triggering_factors = alert.get("triggering_factors", [])
        if triggering_factors:
            indicators.extend(triggering_factors)
        return indicators

    def _parse_audit_from_narrative(self, narrative: str) -> Dict[str, Any]:
        """Extract the audit reasoning section from the generated narrative."""
        audit = {
            "data_sources_used": [],
            "typologies_matched": [],
            "confidence_level": "MEDIUM",
            "key_factors": [],
            "limitations": [],
            "rules_matched": []
        }
        try:
            if "AUDIT TRAIL - REASONING LOG" in narrative:
                audit_section = narrative.split("### AUDIT TRAIL - REASONING LOG")[1]
                lines = audit_section.strip().split("\n")
                current_section = None
                for line in lines:
                    line = line.strip()
                    if "DATA SOURCES USED" in line:
                        current_section = "data_sources"
                    elif "RULES/TYPOLOGIES MATCHED" in line:
                        current_section = "typologies"
                    elif "CONFIDENCE ASSESSMENT" in line:
                        current_section = "confidence"
                    elif "LIMITATIONS" in line:
                        current_section = "limitations"
                    elif line.startswith("- ") and current_section:
                        item = line[2:].strip()
                        if current_section == "data_sources":
                            audit["data_sources_used"].append(item)
                        elif current_section == "typologies":
                            audit["typologies_matched"].append(item)
                            audit["rules_matched"].append(item)
                        elif current_section == "confidence":
                            if "confidence:" in line.lower():
                                for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                                    if level in line.upper():
                                        audit["confidence_level"] = level
                                        break
                            else:
                                audit["key_factors"].append(item)
                        elif current_section == "limitations":
                            audit["limitations"].append(item)
        except Exception as e:
            logger.warning(f"Could not fully parse audit section: {e}")
        return audit

    def generate_narrative(
        self,
        customer_data: Dict,
        alert_data: Dict,
        transaction_data: List[Dict],
        hosting_environment: str = "on-premises"
    ) -> GenerationResult:
        """Generate a SAR narrative with full audit trail."""
        start_time = datetime.utcnow()
        # Retrieve RAG context
        alert_type = alert_data.get("alert_type", "suspicious activity")
        tx_summary = f"Total: {alert_data.get('total_amount', 0)}, Count: {alert_data.get('transaction_count', 0)}"
        rag_context = rag_service.retrieve_all_context(alert_type, tx_summary)
        # Build prompt
        user_prompt = self._build_prompt(
            customer_data, alert_data, transaction_data, rag_context, hosting_environment
        )
        prompt_hash = hashlib.sha256(user_prompt.encode()).hexdigest()[:16]
        try:
            llm = self._get_llm()
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]
            response = llm.invoke(messages)
            narrative = response.content
            tokens_used = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_used = response.usage_metadata.get("total_tokens")
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            narrative = self._generate_template_fallback(customer_data, alert_data, transaction_data)
            tokens_used = None
        # Parse audit trail
        audit = self._parse_audit_from_narrative(narrative)
        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds()
        return GenerationResult(
            narrative=narrative,
            audit_trail={
                "prompt_hash": prompt_hash,
                "model": self._model_name,
                "generation_time_seconds": generation_time,
                "tokens_used": tokens_used,
                "rag_templates_used": [t["id"] for t in rag_context.get("templates", [])],
                "rag_regulations_used": [r["id"] for r in rag_context.get("regulations", [])],
                "risk_indicators_extracted": self._extract_risk_indicators(customer_data, alert_data, transaction_data),
                "hosting_environment": hosting_environment,
                "system_prompt_hash": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:16],
                **audit
            },
            rag_sources=rag_context,
            model_used=self._model_name,
            prompt_hash=prompt_hash,
            generation_time_seconds=generation_time,
            tokens_used=tokens_used,
            confidence_level=audit.get("confidence_level", "MEDIUM"),
            typologies_matched=audit.get("typologies_matched", []),
            data_sources_used=audit.get("data_sources_used", []),
            rules_matched=audit.get("rules_matched", [])
        )

    def _generate_template_fallback(
        self, customer_data: Dict, alert_data: Dict, transaction_data: List[Dict]
    ) -> str:
        """Fallback template when LLM is unavailable."""
        name = customer_data.get("full_name", "UNKNOWN")
        cid = customer_data.get("customer_id", "UNKNOWN")
        amount = alert_data.get("total_amount", 0)
        tx_count = alert_data.get("transaction_count", 0)
        alert_type = alert_data.get("alert_type", "Suspicious Activity")
        dt_start = alert_data.get("date_range_start", "N/A")
        dt_end = alert_data.get("date_range_end", "N/A")
        risk = customer_data.get("risk_rating", "MEDIUM")
        occupation = customer_data.get("occupation", "Unknown")
        return f"""## SUSPICIOUS ACTIVITY REPORT - DRAFT NARRATIVE
**[TEMPLATE-GENERATED - LLM UNAVAILABLE - HUMAN REVIEW REQUIRED]**

---

### 1. EXECUTIVE SUMMARY
This Suspicious Activity Report is filed in respect of {name} (Customer ID: {cid}) 
following detection of {alert_type.replace('_', ' ')} activity. During the reporting period 
{dt_start} to {dt_end}, transactions totalling £{amount:,.2f} across {tx_count} transactions 
were identified as potentially suspicious.

---

### 2. SUBJECT INFORMATION
- **Full Name:** {name}
- **Customer ID:** {cid}
- **Occupation:** {occupation}
- **Risk Rating:** {risk}
- **KYC Status:** {customer_data.get('kyc_status', 'VERIFIED')}
- **PEP Status:** {'YES' if customer_data.get('pep_status') else 'NO'}

---

### 3. DESCRIPTION OF SUSPICIOUS ACTIVITY
The account was flagged for {alert_type.replace('_', ' ')} during the period {dt_start} to {dt_end}. 
The total value of transactions under review amounts to £{amount:,.2f} across {tx_count} individual 
transactions. This activity appears inconsistent with the customer's stated profile.

---

### 4. TIMELINE OF EVENTS
See attached transaction data for full chronological record.

---

### 5. TYPOLOGY MATCH
Based on available data, this activity may match: suspicious transaction patterns.

---

### 6. REGULATORY BASIS FOR FILING
This SAR is filed pursuant to the Proceeds of Crime Act 2002 (POCA), sections 330-332.

---

### 7. CONCLUSION
Recommend human analyst review and completion of this narrative. LLM generation was unavailable.

---

### AUDIT TRAIL - REASONING LOG
DATA SOURCES USED:
- Customer KYC profile (customer_id: {cid})
- Transaction alert data (alert_type: {alert_type})
- Template-based fallback (LLM unavailable)

RULES/TYPOLOGIES MATCHED:
- {alert_type.replace('_', ' ')} pattern detected

CONFIDENCE ASSESSMENT:
- Overall suspicion confidence: LOW
- Key factors driving the assessment: LLM unavailable, requires human review

LIMITATIONS AND CAVEATS:
- This narrative was generated using a template fallback; LLM was not available
- Human analyst MUST review and complete this narrative before submission
"""


sar_generator = SARGenerator()
