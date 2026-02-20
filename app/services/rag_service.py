"""
RAG Service: In-memory TF-IDF retrieval of SAR templates and regulatory guidelines.
Uses scikit-learn for cosine similarity (Python 3.14 compatible).
"""
import os
import logging
from typing import List, Dict, Any, Optional
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.config import settings

logger = logging.getLogger(__name__)

SAR_TEMPLATES = [
    {
        "id": "tmpl_structured_layering",
        "title": "Structuring and Layering - Standard SAR Template",
        "content": (
            "SUSPICIOUS ACTIVITY REPORT - STRUCTURING/LAYERING NARRATIVE TEMPLATE\n\n"
            "SECTION 1: SUBJECT INFORMATION\n"
            "The subject of this report is [CUSTOMER_NAME], account holder at [BANK_NAME] since [OPEN_DATE].\n"
            "The customer is [OCCUPATION] with stated annual income of [INCOME]. KYC classification: [RISK_RATING].\n\n"
            "SECTION 2: SUSPICIOUS ACTIVITY DESCRIPTION\n"
            "During the period [START_DATE] to [END_DATE], the subject conducted [NUM_TRANSACTIONS] transactions\n"
            "totaling [TOTAL_AMOUNT]. The activity is suspicious because: (1) transactions appear structured to\n"
            "avoid reporting thresholds; (2) funds were rapidly layered across multiple accounts;\n"
            "(3) activity is inconsistent with the customer's stated income and occupation.\n\n"
            "SECTION 3: TRANSACTION DETAILS\n"
            "Multiple cash deposits below threshold amounts were observed across [NUM_DAYS] business days.\n"
            "Aggregate deposits totaled [TOTAL_DEPOSIT]. Funds were subsequently transferred to [NUM_ACCOUNTS]\n"
            "different accounts across [NUM_JURISDICTIONS] jurisdictions.\n\n"
            "SECTION 4: TYPOLOGY MATCH\n"
            "This activity matches the following money laundering typologies: Smurfing / Structuring,\n"
            "Trade-Based Money Laundering (if applicable), Layering through Wire Transfers.\n\n"
            "SECTION 5: CONCLUSION\n"
            "Based on the above, [BANK_NAME] believes this activity may constitute money laundering and\n"
            "is therefore filing this SAR."
        ),
        "tags": ["structuring", "layering", "smurfing", "cash deposits", "AML"]
    },
    {
        "id": "tmpl_rapid_movement",
        "title": "Rapid Movement of Funds - Placement to Layering",
        "content": (
            "SUSPICIOUS ACTIVITY REPORT - RAPID FUNDS MOVEMENT NARRATIVE TEMPLATE\n\n"
            "SECTION 1: SUBJECT INFORMATION\n"
            "Subject [CUSTOMER_NAME] (DOB: [DOB], [NATIONALITY]) holds account [ACCOUNT_NUMBER]\n"
            "opened [OPEN_DATE]. Occupation: [OCCUPATION]. PEP Status: [PEP_STATUS].\n\n"
            "SECTION 2: SUSPICIOUS ACTIVITY\n"
            "Between [START_DATE] and [END_DATE], the account received [CREDIT_AMOUNT] from [NUM_SOURCES]\n"
            "distinct sources, then transferred [DEBIT_AMOUNT] outbound within [DAYS_BETWEEN] days.\n"
            "Velocity of fund movement is inconsistent with legitimate business activity.\n\n"
            "SECTION 3: COUNTERPARTY ANALYSIS\n"
            "Incoming funds originated from: [COUNTERPARTY_LIST]. Outbound transfers directed to:\n"
            "[BENEFICIARY_LIST]. Several counterparties are in high-risk jurisdictions: [HIGH_RISK_JURISDICTIONS].\n\n"
            "SECTION 4: WHY THIS IS SUSPICIOUS\n"
            "- Funds received from [NUM_SOURCES] unique senders in rapid succession\n"
            "- Near-immediate onward transfer without commercial purpose\n"
            "- Counterparties are unrelated to the customer's stated business\n"
            "- Geographic pattern inconsistent with customer profile\n\n"
            "SECTION 5: REGULATORY REFERENCE\n"
            "Matches FATF Typology: Rapid movement / Round-tripping. Ref: FIU-IND STR Guidelines, RBI Master Direction on KYC 2016, Section 12 PMLA 2002."
        ),
        "tags": ["rapid movement", "round-tripping", "wire transfers", "high-risk jurisdictions"]
    },
    {
        "id": "tmpl_trade_based",
        "title": "Trade-Based Money Laundering (TBML)",
        "content": (
            "SUSPICIOUS ACTIVITY REPORT - TRADE-BASED MONEY LAUNDERING\n\n"
            "SECTION 1: SUBJECT PROFILE\n"
            "Company: [COMPANY_NAME], incorporated [DATE] in [JURISDICTION]. Director: [DIRECTOR_NAME].\n"
            "Business type: [BUSINESS_TYPE]. Avg monthly turnover: [MONTHLY_TURNOVER].\n\n"
            "SECTION 2: SUSPICIOUS TRADE ACTIVITY\n"
            "Account received [NUM] payments described as [INVOICE_DESC] totaling [AMOUNT] from\n"
            "[COUNTERPARTY] in [COUNTRY]. Invoice amounts appear inconsistent with market pricing.\n"
            "[OVER_UNDER] invoicing is suspected.\n\n"
            "SECTION 3: RED FLAGS\n"
            "- Invoiced goods value significantly above/below market rate\n"
            "- Counterparty in FATF grey/blacklisted jurisdiction\n"
            "- Payments through multiple intermediaries with no commercial rationale\n"
            "- Discrepancy between goods description and customer SIC code\n\n"
            "SECTION 4: TYPOLOGY\n"
            "Trade-Based Money Laundering through over/under-invoicing. Ref: FATF Report on TBML 2006."
        ),
        "tags": ["TBML", "trade finance", "over-invoicing", "under-invoicing", "import export"]
    },
    {
        "id": "tmpl_fraud_proceeds",
        "title": "Receipt of Fraud Proceeds / Mule Account",
        "content": (
            "SUSPICIOUS ACTIVITY REPORT - SUSPECTED FRAUD PROCEEDS / MULE ACCOUNT\n\n"
            "SECTION 1: SUBJECT\n"
            "[CUSTOMER_NAME], account opened [DATE]. Profile inconsistency: [INCONSISTENCY_NOTES].\n\n"
            "SECTION 2: FRAUD INDICATORS\n"
            "Account received [AMOUNT] credited on [DATE] from [SOURCE] shortly after account opening.\n"
            "Funds withdrawn/transferred within [HOURS] hours. Pattern consistent with a money mule account.\n\n"
            "SECTION 3: VICTIM/FRAUD LINK\n"
            "A potential link to [FRAUD_TYPE] fraud has been identified. Victim complaints received: [NUM_COMPLAINTS].\n"
            "Law enforcement referral: [LEA_REF] (if applicable).\n\n"
            "SECTION 4: ACTION TAKEN\n"
            "Account placed under enhanced monitoring. Payments blocked pending investigation.\n"
            "External STR filed with FIU-IND (reference: [FIU_STR_REF]). Reported to local Cyber Crime Cell (ref: [CYBERCRIME_REF]) where applicable."
        ),
        "tags": ["fraud", "mule account", "APP fraud", "consumer fraud", "cyber fraud"]
    },
    {
        "id": "tmpl_high_risk_jurisdiction",
        "title": "High-Risk Jurisdiction Cross-Border Transfers",
        "content": (
            "SUSPICIOUS ACTIVITY REPORT - HIGH RISK JURISDICTION TRANSFERS\n\n"
            "SECTION 1: CUSTOMER BACKGROUND\n"
            "[CUSTOMER_NAME] is a [CUSTOMER_TYPE] customer with [RISK_RATING] risk rating.\n"
            "Jurisdiction of concern: [JURISDICTION]. FATF Status: [FATF_STATUS].\n\n"
            "SECTION 2: TRANSACTION OVERVIEW\n"
            "[NUM_TRANSFERS] international wire transfers totaling [TOTAL_AMOUNT] sent to/received from\n"
            "[COUNTRY] between [DATE_FROM] and [DATE_TO]. Beneficiaries: [BENEFICIARY_LIST].\n\n"
            "SECTION 3: REGULATORY CONCERN\n"
            "[COUNTRY] is identified on Ministry of Finance / FATF grey list / OFAC SDN list / RBI advisory on high-risk jurisdictions.\n"
            "Transfers lack credible business justification. Customer unable to provide satisfactory\n"
            "explanation for the nature of these transactions.\n\n"
            "SECTION 4: CONCLUSION\n"
            "Activity reported under PMLA 2002, Section 12 — STR filed with FIU-IND within 7 days of detection. Possible Terrorism Financing / Sanctions Evasion under UAPA."
        ),
        "tags": ["high-risk jurisdiction", "sanctions", "FATF", "cross-border", "wire transfer"]
    }
]

REGULATORY_GUIDELINES = [
    {
        "id": "reg_pmla_2002",
        "title": "Prevention of Money Laundering Act 2002 (PMLA) - STR Filing Requirements",
        "content": """PREVENTION OF MONEY LAUNDERING ACT 2002 (INDIA) - STR FILING OBLIGATIONS

Under Section 12 of PMLA 2002, every banking company, financial institution, and intermediary
must maintain records and furnish information of suspicious transactions to FIU-IND.

KEY REQUIREMENTS:
1. Filing Deadline: STRs must be filed within 7 working days of forming suspicion.
2. CTR Threshold: Cash transactions of ₹10,00,000 (₹10 lakh) or more must be reported as CTR.
3. STR Obligation: Any transaction (regardless of amount) that appears suspicious must be filed as STR.
4. Non-Tipping Off: Section 12A prohibits disclosure to the subject of investigation.
5. Penalty for non-filing: Up to 7 years rigorous imprisonment; fine up to ₹5,00,000 under Section 13 PMLA.
6. Enforcement: Enforcement Directorate (ED) investigates PMLA violations; CBI for predicate offences.

NARRATIVE STANDARDS:
- Must include: who, what, when, where, why suspicious
- Must reference specific transactions with dates, amounts, accounts
- Should reference applicable money laundering typology per FATF/FIU-IND guidance
- Must be factual, objective, and not speculative without evidential basis
- All amounts in INR (₹) using Indian numbering system (lakhs, crores)""",
        "tags": ["PMLA", "India law", "FIU-IND", "STR filing", "CTR", "ED", "RBI"]
    },
    {
        "id": "reg_rbi_kyc_directions",
        "title": "RBI Master Directions on KYC 2016 - AML/CFT Obligations",
        "content": """RESERVE BANK OF INDIA - MASTER DIRECTIONS ON KYC 2016 (UPDATED)

STR/SAR NARRATIVE BEST PRACTICE (per RBI and IBA Guidelines):

1. CLARITY: Narratives should describe clearly why activity is suspicious.
   Avoid jargon. Write in plain language for review by FIU-IND analysts.

2. COMPLETENESS - A good STR narrative answers:
   WHO is involved (customer details, KYC data, counterparties)
   WHAT activity occurred (transaction details, amounts, dates, channels — NEFT/RTGS/IMPS/UPI)
   WHEN the activity took place (date range, frequency)
   WHERE the activity occurred (accounts, branches, jurisdictions)
   WHY it is suspicious (deviation from norms, red flags, typology match)
   HOW it was detected (transaction monitoring rule, branch staff referral, etc.)

3. PROPORTIONALITY: Narrative length should match complexity of the activity.

4. OBJECTIVITY: State facts. Avoid unsupported opinion.
   Say 'customer was unable to provide satisfactory explanation' not 'customer lied'.

5. TYPOLOGY REFERENCE: Reference recognised ML/TF typologies per FATF, FIU-IND Annual Reports.

6. PEP/SANCTIONS SCREENING: Mandatory screening against UN Consolidated List, MHA lists, RBI caution lists.""",
        "tags": ["RBI", "KYC", "AML", "CFT", "narrative standards", "India", "FIU-IND"]
    },
    {
        "id": "reg_fatf_typologies",
        "title": "FATF Money Laundering Typologies Reference (India Context)",
        "content": """FINANCIAL ACTION TASK FORCE (FATF) - MONEY LAUNDERING TYPOLOGIES (INDIA CONTEXT)

1. STRUCTURING (SMURFING): Breaking large amounts into smaller deposits to avoid RBI CTR threshold
   of ₹10,00,000. Red flag: Multiple cash deposits just below ₹10 lakh.

2. LAYERING VIA NEFT/RTGS/IMPS: Rapid movement of funds through multiple accounts.
   Red flag: Frequent transfers with no commercial purpose; pass-through pattern.

3. TRADE-BASED MONEY LAUNDERING (TBML): Disguising proceeds through import/export invoices.
   Red flags: Over/under invoicing; misrepresentation of goods; GST mismatches.

4. REAL ESTATE LAUNDERING: Using property transactions. Common in India.
   Red flags: All-cash or undeclared payments; benami property; stamp duty undervaluation.

5. SHELL COMPANY / HAWALA: Using companies or informal value transfer to distance criminal from funds.
   Red flags: Complex MCA21 ownership structures; ED-monitored hawala networks.

6. CRYPTOCURRENCY / UPI FRAUD: Converting proceeds through virtual assets or UPI networks.
   Red flags: P2P crypto exchanges; mule UPI accounts; SIM swap fraud proceeds.

7. TERRORISM FINANCING (under UAPA): Funding terrorist activity.
   Red flags: Transfers to UAPA-designated entities; links to conflict regions.

8. ROUND-TRIPPING: Funds moved outside India and returned as FDI to disguise origin.
   Red flags: Mauritius/Singapore/Cayman routes; FEMA violation indicators.""",
        "tags": ["FATF", "typologies", "structuring", "layering", "TBML", "hawala", "India"]
    },
    {
        "id": "reg_fiu_ind_guidelines",
        "title": "FIU-IND Reporting Guidelines for Scheduled Commercial Banks",
        "content": """FINANCIAL INTELLIGENCE UNIT – INDIA (FIU-IND) REPORTING GUIDELINES

FIU-IND is the national agency under the Ministry of Finance responsible for receiving,
processing, analysing and disseminating financial intelligence under PMLA 2002.

REPORTING ENTITIES (Banks, NBFCs, Regulated Entities):

1. SUSPICIOUS TRANSACTION REPORT (STR): Filed where transaction arouses suspicion of ML/TF
   regardless of amount. Filed within 7 working days via FINnet Gateway.

2. CASH TRANSACTION REPORT (CTR): All cash transactions ≥ ₹10,00,000 in a single day
   (aggregate per customer). Filed by 15th of following month.

3. COUNTERFEIT CURRENCY REPORT (CCR): Report fake currency notes detected.

4. NON-PROFIT ORGANISATION REPORT (NTR): Transactions of NPOs meeting threshold criteria.

5. CROSS BORDER WIRE TRANSFER REPORT (CBWTR): Inbound/outbound wire transfers ≥ ₹5,00,000.

PRINCIPAL OFFICER (PO): Designated MLRO equivalent responsible for filing with FIU-IND.
Must maintain audit trail of all STR decisions (filed or not filed + rationale).

FINnet 2.0: Current digital reporting portal for all FIU-IND submissions.""",
        "tags": ["FIU-IND", "STR", "CTR", "CBWTR", "FINnet", "PMLA", "India"]
    },
    {
        "id": "reg_aml_red_flags_india",
        "title": "Key AML Red Flag Indicators for Indian Banks (RBI/IBA Guidance)",
        "content": """AML RED FLAG INDICATORS - INDIAN BANKING CONTEXT (RBI/IBA)

CUSTOMER BEHAVIOUR RED FLAGS:
- Reluctance to provide KYC documents (Aadhaar, PAN, VCIPL)
- Inconsistent explanations for transactions
- Transactions inconsistent with stated business/income (ITR mismatch)
- Sudden reactivation of dormant account with high-value transactions
- Multiple accounts at different branches for no apparent reason

TRANSACTION RED FLAGS:
- Cash deposits just below ₹10,00,000 RBI CTR threshold (structuring)
- Rapid NEFT/RTGS/IMPS movement with no apparent business purpose
- Round-number transactions (₹9,99,000 or ₹49,000 — below PAN threshold)
- IMPS/UPI transactions to multiple unrelated beneficiaries
- Immediate withdrawal of deposited funds ("in-out" pattern)
- Unexplained significant jump in monthly transaction volume

ACCOUNT/PRODUCT RED FLAGS:
- New account (<6 months) receiving large credits immediately
- Personal account used for business-scale transactions (GST turnover mismatch)
- International remittances under FEMA to high-risk jurisdictions
- Multiple demand drafts/cash payments to single entity below reporting threshold

COUNTERPARTY RED FLAGS:
- Counterparties on UAPA/UN/OFAC/MHA designated lists
- Counterparties in FATF grey/blacklisted countries (per RBI advisory)
- Transactions with no apparent relationship between customer and beneficiary
- Benami accounts or shell companies as counterparties""",
        "tags": ["red flags", "AML indicators", "India", "RBI", "IBA", "KYC", "suspicious activity"]
    }
]


class RAGService:
    """
    In-memory RAG service using TF-IDF cosine similarity.
    Fully compatible with Python 3.14 — no chromadb or pydantic v1 required.
    """

    def __init__(self):
        self._templates: List[Dict[str, Any]] = []
        self._regulations: List[Dict[str, Any]] = []
        self._initialized = False
        # Lazy-imported sklearn components
        self._vectorizer = None
        self._tmpl_matrix = None
        self._reg_matrix = None
        self._tmpl_vectorizer = None
        self._reg_vectorizer = None

    def initialize(self):
        """Load documents into memory and build TF-IDF matrices."""
        if self._initialized:
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._templates = [
                {
                    "id": t["id"],
                    "content": t["content"],
                    "metadata": {"title": t["title"], "tags": ",".join(t["tags"])}
                }
                for t in SAR_TEMPLATES
            ]
            self._regulations = [
                {
                    "id": r["id"],
                    "content": r["content"],
                    "metadata": {"title": r["title"], "tags": ",".join(r["tags"])}
                }
                for r in REGULATORY_GUIDELINES
            ]
            # Build TF-IDF matrices for fast cosine retrieval
            tmpl_corpus = [t["content"] + " " + t["metadata"]["tags"] for t in self._templates]
            reg_corpus = [r["content"] + " " + r["metadata"]["tags"] for r in self._regulations]
            self._tmpl_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            self._tmpl_matrix = self._tmpl_vectorizer.fit_transform(tmpl_corpus)
            self._reg_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            self._reg_matrix = self._reg_vectorizer.fit_transform(reg_corpus)
            self._initialized = True
            logger.info("RAG Service initialized (in-memory TF-IDF mode).")
        except ImportError:
            logger.warning("scikit-learn not available; RAG service will use keyword fallback.")
            self._templates = [{"id": t["id"], "content": t["content"], "metadata": {"title": t["title"], "tags": ",".join(t["tags"])}} for t in SAR_TEMPLATES]
            self._regulations = [{"id": r["id"], "content": r["content"], "metadata": {"title": r["title"], "tags": ",".join(r["tags"])}} for r in REGULATORY_GUIDELINES]
            self._initialized = True
        except Exception as e:
            logger.error(f"RAG Service init error: {e}")
            self._initialized = True  # Mark as initialized to avoid infinite retries

    def _tfidf_retrieve(self, query: str, docs: List[Dict], vectorizer, matrix, n: int) -> List[Dict]:
        """Retrieve top-n documents by TF-IDF cosine similarity."""
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            q_vec = vectorizer.transform([query])
            scores = cosine_similarity(q_vec, matrix).flatten()
            top_idx = np.argsort(scores)[::-1][:n]
            return [
                {**docs[i], "distance": float(1.0 - scores[i])}
                for i in top_idx if scores[i] > 0
            ]
        except Exception:
            return docs[:n]

    def _keyword_retrieve(self, query: str, docs: List[Dict], n: int) -> List[Dict]:
        """Simple keyword-based fallback retrieval."""
        query_words = set(query.lower().split())
        scored = []
        for doc in docs:
            text = (doc["content"] + " " + doc["metadata"].get("tags", "")).lower()
            score = sum(1 for w in query_words if w in text)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"distance": 0.0, **d} for _, d in scored[:n]]

    def retrieve_templates(self, query: str, n_results: int = 2) -> List[Dict[str, Any]]:
        """Retrieve relevant SAR narrative templates for the given query."""
        if not self._initialized:
            self.initialize()
        if self._tmpl_vectorizer is not None and self._tmpl_matrix is not None:
            return self._tfidf_retrieve(query, self._templates, self._tmpl_vectorizer, self._tmpl_matrix, n_results)
        return self._keyword_retrieve(query, self._templates, n_results)

    def retrieve_regulations(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant regulatory guidelines for the given query."""
        if not self._initialized:
            self.initialize()
        if self._reg_vectorizer is not None and self._reg_matrix is not None:
            return self._tfidf_retrieve(query, self._regulations, self._reg_vectorizer, self._reg_matrix, n_results)
        return self._keyword_retrieve(query, self._regulations, n_results)

    def retrieve_all_context(self, alert_type: str, transaction_summary: str) -> Dict[str, List[Dict]]:
        """Retrieve both templates and regulations for a given case context."""
        query = f"{alert_type} {transaction_summary}"
        return {
            "templates": self.retrieve_templates(query, n_results=2),
            "regulations": self.retrieve_regulations(query, n_results=3)
        }


rag_service = RAGService()