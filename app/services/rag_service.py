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
            "Matches FATF Typology: Rapid movement / Round-tripping. Ref: JMLSG Guidance Part I Chapter 6."
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
            "External report filed with Action Fraud (reference: [ACTIONFRAUD_REF])."
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
            "[COUNTRY] is identified on HM Treasury sanctions list / FATF grey list / OFAC SDN list.\n"
            "Transfers lack credible business justification. Customer unable to provide satisfactory\n"
            "explanation for the nature of these transactions.\n\n"
            "SECTION 4: CONCLUSION\n"
            "Activity reported under Terrorism Financing / Sanctions Evasion / AML obligations."
        ),
        "tags": ["high-risk jurisdiction", "sanctions", "FATF", "cross-border", "wire transfer"]
    }
]

REGULATORY_GUIDELINES = [
    {
        "id": "reg_poca_2002",
        "title": "Proceeds of Crime Act 2002 (POCA) - SAR Filing Requirements",
        "content": """PROCEEDS OF CRIME ACT 2002 (UK) - SAR FILING OBLIGATIONS

Under the Proceeds of Crime Act 2002, a Suspicious Activity Report (SAR) must be submitted 
to the National Crime Agency (NCA) where a person knows or suspects, or has reasonable grounds 
for knowing or suspecting, that another person is engaged in money laundering.

KEY REQUIREMENTS:
1. Filing Deadline: SARs must be filed promptly; for consent SARs, within 7 days of request.
2. Defence Against Money Laundering (DAML): Section 335-338 provide immunity from prosecution 
   when consent obtained from NCA prior to completing a transaction.
3. Tipping Off: Section 333A prohibits disclosure to subject of investigation.
4. Penalty for non-filing: Up to 14 years imprisonment; unlimited fines for firms.

NARRATIVE STANDARDS:
- Must include: who, what, when, where, why suspicious
- Must reference specific transactions with dates, amounts, accounts
- Should reference applicable money laundering typology
- Must be factual, objective, and not speculative without evidential basis""",
        "tags": ["POCA", "UK law", "NCA", "SAR filing", "DAML", "tipping off"]
    },
    {
        "id": "reg_jmlsg_guidance",
        "title": "JMLSG Guidance - SAR Narrative Standards",
        "content": """JOINT MONEY LAUNDERING STEERING GROUP (JMLSG) GUIDANCE

SAR NARRATIVE BEST PRACTICE:

1. CLARITY: Narratives should be written in plain English, clearly describing why activity 
   is suspicious. Avoid jargon or abbreviations without explanation.

2. COMPLETENESS - A good SAR narrative answers:
   WHO is involved (subject details, counterparties)
   WHAT activity occurred (transaction details, amounts, dates)
   WHEN the activity took place (date range, frequency)
   WHERE the activity occurred (accounts, jurisdictions)
   WHY it is suspicious (deviation from norms, red flags, typology match)
   HOW it was detected (monitoring rule, staff referral, etc.)

3. PROPORTIONALITY: Narrative length and complexity should be proportionate to complexity 
   of underlying activity. Complex schemes require detailed narratives.

4. OBJECTIVITY: State facts. Avoid opinion unsupported by evidence. 
   Say 'the customer was unable to provide satisfactory explanation' not 'the customer lied'.

5. TYPOLOGY REFERENCE: Reference recognised money laundering or terrorist financing typologies 
   where applicable (FATF, NCA, HMRC guidance).""",
        "tags": ["JMLSG", "narrative standards", "best practice", "5W1H", "UK AML"]
    },
    {
        "id": "reg_fatf_typologies",
        "title": "FATF Money Laundering Typologies Reference",
        "content": """FINANCIAL ACTION TASK FORCE (FATF) - MONEY LAUNDERING TYPOLOGIES

1. STRUCTURING (SMURFING): Breaking large amounts into smaller amounts deposited separately 
   to avoid reporting thresholds. Red flag: Multiple cash deposits just below threshold.

2. LAYERING VIA WIRE TRANSFERS: Rapid movement of funds through multiple accounts/jurisdictions 
   to obscure origin. Red flag: Frequent int'l transfers with no commercial purpose.

3. TRADE-BASED MONEY LAUNDERING (TBML): Disguising proceeds through trade transactions. 
   Red flags: Over/under invoicing, multiple invoicing, misrepresentation of goods.

4. REAL ESTATE LAUNDERING: Using property transactions to launder proceeds. 
   Red flags: All-cash transactions, property flipping, third-party payments.

5. SHELL COMPANY / NOMINEE USE: Using corporate vehicles to distance criminal from funds. 
   Red flags: Complex ownership, bearer shares, nominee directors.

6. CRYPTOCURRENCY CONVERSION: Converting proceeds through virtual assets. 
   Red flags: P2P exchanges, mixing services, privacy coins.

7. TERRORISM FINANCING: Funding terrorist activity, may involve small amounts. 
   Red flags: Transfers to conflict regions, payments to listed individuals/entities.

8. PROLIFERATION FINANCING: Financing weapons of mass destruction programs.
   Red flags: Transactions linked to designated entities, dual-use goods.""",
        "tags": ["FATF", "typologies", "structuring", "layering", "TBML", "terrorism financing"]
    },
    {
        "id": "reg_fca_requirements",
        "title": "FCA SYSC Rules on AML Suspicious Activity Reporting",
        "content": """FCA SYSTEMS AND CONTROLS (SYSC) - AML OBLIGATIONS

Under FCA SYSC 3.2.6R and 6.3.1R, regulated firms must:

1. APPOINTMENT OF MLRO: Designated Money Laundering Reporting Officer responsible for 
   receiving internal SARs and deciding whether to submit to NCA.

2. INTERNAL SAR PROCESS: Staff must report suspicions to MLRO. MLRO evaluates and 
   determines whether external SAR submission is required. Documented decision trail mandatory.

3. RECORD KEEPING: All SAR-related records must be retained for minimum 5 years (POCA S.337).
   Records include: transaction records, customer due diligence, SAR text, reasons for filing.

4. TRAINING: All relevant staff must receive regular AML/CTF training including SAR obligations.

5. QUALITY OF SARs: FCA expects SARs to be of sufficient quality to enable NCA to assess 
   whether further action is warranted. Poor quality SARs may constitute a regulatory breach.

THEMATIC GUIDANCE: FCA Financial Crime Guide (FCG) provides detailed sector-specific guidance 
on suspicious activity indicators and appropriate SAR content.""",
        "tags": ["FCA", "SYSC", "MLRO", "record keeping", "UK regulation", "compliance"]
    },
    {
        "id": "reg_aml_red_flags",
        "title": "Key AML Red Flag Indicators for SAR Narratives",
        "content": """AML RED FLAG INDICATORS - FOR SAR NARRATIVE REFERENCE

CUSTOMER BEHAVIOUR RED FLAGS:
- Reluctance to provide KYC documentation
- Inconsistent explanations for transactions
- Transactions inconsistent with stated business/income
- Sudden change in transaction patterns
- Use of multiple accounts for no apparent reason

TRANSACTION RED FLAGS:
- Cash transactions just below reporting thresholds (structuring)
- Rapid movement of funds with no apparent business purpose
- Round-number transactions (e.g., exactly ₹9,999 or ₹99,999)
- Transactions with high-risk counterparties or jurisdictions
- Unexplained significant increases in transaction volume/value
- Immediate withdrawal of deposited funds ("in-out" pattern)
- Unusual geographic dispersion of senders/recipients

ACCOUNT/PRODUCT RED FLAGS:
- New account receiving immediate large credits
- Account dormancy followed by sudden reactivation with high-value transactions
- Use of personal accounts for business transactions
- International wire transfers to/from high-risk countries
- Multiple third-party payments to a single beneficiary

COUNTERPARTY RED FLAGS:
- Counterparties on sanctions/PEP lists
- Counterparties in FATF grey/blacklisted jurisdictions
- No apparent relationship between customer and counterparty
- Use of intermediaries with no business justification""",
        "tags": ["red flags", "AML indicators", "suspicious activity", "typology", "detection"]
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