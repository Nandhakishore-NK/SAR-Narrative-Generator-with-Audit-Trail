# SOLUTION — SAR Narrative Generator with AI-Powered Audit Trail
### Barclays AML Compliance Platform | Hackathon Presentation

---

## Problem Statement

AML (Anti-Money Laundering) analysts at Barclays manually write Suspicious Activity Reports (SARs) every time a transaction alert is flagged. Each report takes **5–6 hours** of analyst time — reviewing transaction history, matching money laundering typologies, referencing regulatory guidelines (POCA 2002, JMLSG, FATF), drafting a narrative, and assembling audit evidence. This is slow, inconsistent, and error-prone at scale.

---

## How It Solves the Problem

Our system automates the full SAR lifecycle end-to-end using AI:

1. **Ingest** — KYC profile + transaction alert data is loaded per case
2. **Retrieve** — A RAG (Retrieval-Augmented Generation) pipeline fetches the most relevant SAR templates and regulatory references using TF-IDF cosine similarity
3. **Generate** — An LLM (GPT-4o / Azure OpenAI / local Ollama) produces a structured, regulator-ready narrative following the 5W1H framework with JMLSG and POCA 2002 compliance language built-in
4. **Review** — Analysts edit the draft; Supervisors approve it before filing — enforcing human-in-the-loop accountability
5. **Audit** — Every AI decision, prompt hash, data source, typology match, and approval action is logged immutably to an audit trail
6. **Alert** — Real-time in-app alerts notify relevant users of HIGH/CRITICAL cases instantly

This reduces SAR production time from **5–6 hours → ~15 minutes** while maintaining full regulatory defensibility.

---

## Impact Metrics

| Category | Metric to Measure |
|---|---|
| **Efficiency** | Average time per SAR before vs. after (target: 90%+ reduction) |
| **Quality** | Typology match accuracy; regulatory citation coverage rate per narrative |
| **Compliance** | % of SARs with complete audit trail; zero SARs filed without supervisor approval |
| **Risk Reduction** | False positive alert closure rate; escalation-to-SAR conversion rate |
| **Adoption** | Active users per role per week; pages visited per session |
| **Throughput** | Number of SARs generated / reviewed / approved per week |
| **Cost Saving** | Analyst hours saved × average hourly cost of compliance staff |

---

## Frameworks / Tools / Technology Stack

| Layer | Technology | Role |
|---|---|---|
| **Frontend / UI** | Streamlit 1.32 | Internal compliance dashboard — no separate frontend build pipeline |
| **AI Orchestration** | LangChain + LangChain-OpenAI | Prompt chaining, structured output, audit callback hooks |
| **LLM Backend** | OpenAI GPT-4o / Azure OpenAI / Ollama | SAR narrative generation — swappable via config |
| **RAG Pipeline** | TF-IDF + Cosine Similarity (scikit-learn) | Retrieves SAR templates & regulatory docs (POCA, JMLSG, FATF) per case |
| **Database** | SQLite (dev) → PostgreSQL (prod) | Cases, audit trail, alerts, users — same ORM for both |
| **Auth & RBAC** | bcrypt + custom session auth | Role-gated access: Admin / Supervisor / Analyst / Read-Only |
| **Export** | FPDF2 + openpyxl | PDF SAR narratives + CSV audit log downloads |
| **Containerisation** | Docker + Docker Compose | Reproducible deployment across on-prem / cloud / multi-cloud |
| **Configuration** | python-dotenv + Pydantic Settings | Environment-aware settings (LLM provider, DB URL, SMTP, hosting type) |

---

## Assumptions, Constraints & Solution Decision Points

| Item | Decision | Reason |
|---|---|---|
| **LLM is swappable** | `LLM_PROVIDER` env var supports `openai`, `azure`, `ollama` | Avoids vendor lock-in; supports air-gapped on-prem deployment with local Llama |
| **SQLite for dev** | Zero infrastructure for rapid prototyping | Same SQLAlchemy ORM targets PostgreSQL in production with a single config change |
| **TF-IDF over ChromaDB** | Used scikit-learn for RAG retrieval | Python 3.14 has no ChromaDB wheel yet; scikit-learn is pure-Python and fully compatible |
| **Streamlit over Django/React** | Chose rapid internal tooling framework | Internal compliance tool — delivery speed and analyst UX matter more than UI polish |
| **Human approval is mandatory** | Every AI-generated SAR requires supervisor sign-off | Satisfies FCA SYSC 6.3 requirement; AI assists, humans decide |
| **Immutable audit log** | Audit table is insert-only (no UPDATE/DELETE in code) | Satisfies NCA SAR defensibility requirements — every AI action is traceable |
| **Hosting-environment-aware prompts** | System prompt adapts language based on `HOSTING_ENVIRONMENT` | On-prem emphasises data residency; cloud notes encryption-at-rest and data sovereignty |
| **pages/ renamed to views/** | Avoids Streamlit's automatic multi-page detection | Prevents Streamlit from exposing raw pages without login/session context |

---

## Implementation Ease & Effectiveness

- **Setup time: ~10 minutes** — `pip install -r requirements.txt`, set `OPENAI_API_KEY` in `.env`, run `python run.py`
- **No ML training required** — leverages a pre-trained LLM via API; works out of the box
- **5 pre-seeded sample cases** (STRUCTURING, HIGH_RISK_JURISDICTION, RAPID_MOVEMENT, MULE_ACCOUNT, TBML) allow immediate demo without real data
- **Plug-and-replace LLM** — switching from GPT-4o to Azure OpenAI or a local Llama model requires only a single `.env` line change
- **High effectiveness** — RAG grounds the LLM in known SAR templates and regulatory text, significantly reducing hallucination risk compared to a raw LLM prompt
- **Docker-ready** — `docker compose up --build` deploys the entire stack in one command for consistent environments

---

## Scalability & Usability

### Scalability
- **Horizontal scaling** — Streamlit app is stateless; multiple instances can run behind a load balancer sharing a single PostgreSQL database
- **RAG corpus growth** — TF-IDF index is rebuilt in-memory per instance; can be upgraded to a persistent vector DB (pgvector, ChromaDB) as the template library grows beyond hundreds of documents
- **Database migration path** — SQLite (dev) → PostgreSQL (prod) with zero code changes; connection string driven by `DATABASE_URL` env var
- **Container orchestration** — Docker Compose → Kubernetes migration is straightforward; services are already containerised and stateless

### Usability
- **Role-specific navigation** — Read-Only users never see approval controls; Analysts never see User Management; UI adapts to role automatically
- **Demo credentials on login page** — Zero onboarding friction for evaluators and new users
- **PDF & CSV export** — Narratives downloadable as PDF; full audit logs downloadable as CSV for offline regulatory handover
- **Human-readable audit trail** — In-app log viewer + machine-readable export for compliance team reviews
- **Real-time alert centre** — HIGH/CRITICAL cases surface instantly in the sidebar without page refresh

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT UI (Port 8501)                      │
│  Dashboard | SAR Generator | Review/Approve | Audit | Alerts    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      APPLICATION LAYER                           │
│                                                                  │
│   SAR Generator (LangChain + LLM)                               │
│   RAG Service (TF-IDF / scikit-learn)                           │
│   Audit Service (Immutable insert-only log)                      │
│   Alert Service (Real-time notifications)                        │
│   RBAC / Auth (bcrypt + session)                                 │
│   Data Processor (KYC + transaction parser)                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                        DATA LAYER                                │
│                                                                  │
│   SQLite / PostgreSQL        SAR Templates + Regulations         │
│   (Cases, Users, Audit,      (TF-IDF in-memory index)           │
│    Alerts, Approvals)                                            │
│                              LLM API                             │
│                              (OpenAI / Azure / Ollama)           │
└─────────────────────────────────────────────────────────────────┘
```

---

*Built for Barclays AML Compliance | February 2026*
