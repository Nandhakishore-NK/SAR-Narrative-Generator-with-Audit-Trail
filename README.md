# SAR Narrative Generator with Audit Trail
### Barclays AML Compliance Platform

An AI-powered system for generating, reviewing, and filing Suspicious Activity Reports (SARs) with full regulatory audit trail — reducing analyst effort from 5–6 hours per report to minutes while maintaining complete transparency and defensibility.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT UI (Port 8501)                      │
│  Dashboard | SAR Generator | Review/Approve | Audit | Alerts    │
└───────────────────┬─────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────────┐
│                    APPLICATION LAYER                             │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  SAR Generator  │  │  Audit Service  │  │  Alert Service  │ │
│  │  (LangChain +   │  │  (Immutable     │  │  (Real-time     │ │
│  │   LLM)          │  │   audit trail)  │  │   notifications)│ │
│  └────────┬────────┘  └─────────────────┘  └─────────────────┘ │
│           │                                                      │
│  ┌────────▼────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   RAG Service   │  │  RBAC/Auth      │  │  Data Processor │ │
│  │  (ChromaDB)     │  │  (Role-Based    │  │  (KYC + Txn     │ │
│  │                 │  │   Access Ctrl)  │  │   Data Parser)  │ │
│  └────────┬────────┘  └─────────────────┘  └─────────────────┘ │
└───────────┼─────────────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────────┐
│                     DATA LAYER                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  SQLite / PG    │  │    ChromaDB     │  │    LLM API      │ │
│  │  (Cases, Audit, │  │  (SAR Templates │  │  (OpenAI GPT-4o │ │
│  │   Alerts, Users)│  │   + Regulations)│  │   / Azure /     │ │
│  └─────────────────┘  └─────────────────┘  │   Ollama/Local) │ │
│                                             └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Description |
|---|---|
| **AI Narrative Generation** | LangChain + GPT-4o/Claude/Llama generates regulator-ready SAR narratives |
| **RAG Pipeline** | ChromaDB stores 5 SAR templates + 5 regulatory guidelines (POCA, JMLSG, FATF) retrieved per case |
| **Full Audit Trail** | Every AI decision, data source, typology match, and prompt hash logged immutably |
| **Human Review Workflow** | Analysts edit, supervisors approve; version history tracked |
| **Role-Based Access Control** | Admin / Supervisor / Analyst / Read-Only with domain boundary enforcement |
| **Real-time Alerts** | In-app alert centre + optional email notifications for HIGH/CRITICAL cases |
| **5 Pre-loaded Sample Cases** | STRUCTURING, HIGH_RISK_JURISDICTION, RAPID_MOVEMENT, MULE_ACCOUNT, TBML |
| **Analytics Dashboard** | Case status, alert severity, jurisdiction heatmap, audit event breakdown |
| **Hosting-Environment Aware** | Tailors compliance language for on-premises / cloud-aws / azure / multi-cloud |
| **Horizontal Scalability** | Stateless Streamlit + shared SQLite/PostgreSQL supports multiple instances |
| **PDF/CSV Export** | Download narratives and audit logs |

---

## Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key (or configure Ollama for local LLM)

### 1. Clone and install

```bash
cd "C:\Users\nandh\OneDrive\Desktop\BARCLAYS"
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

**.env minimum configuration:**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...your-key...
OPENAI_MODEL=gpt-4o
```

### 3. Run the application

```bash
python run.py
# OR
streamlit run app/main.py
```

Open **http://localhost:8501** in your browser.

### 4. Demo Credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `Admin@2024!` | Full system access |
| `analyst1` | `Analyst@2024!` | Generate & edit SARs |
| `supervisor1` | `Supervisor@2024!` | Approve SARs |
| `readonly1` | `Readonly@2024!` | View only |

---

## LLM Configuration

The system is provider-agnostic. Configure in `.env`:

### OpenAI (Default)
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o          # or gpt-4-turbo, gpt-3.5-turbo
```

### Azure OpenAI
```env
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### Local (Ollama — Llama 3.1 / Mistral)
```bash
# Install Ollama: https://ollama.ai
ollama pull llama3.1
```
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

---

## Docker Deployment

```bash
# Build and run
docker-compose up --build

# Scale horizontally (3 instances)
docker-compose up --scale sar-app=3
```

---

## Production: PostgreSQL

Replace SQLite with PostgreSQL for production:

```env
DATABASE_URL=postgresql://sar_user:password@localhost:5432/sar_db
```

Uncomment the `postgres:` service in `docker-compose.yml`.

---

## Project Structure

```
BARCLAYS/
├── app/
│   ├── main.py                    # Streamlit entry point + login wall
│   ├── config.py                  # All configuration settings
│   ├── models/
│   │   └── database.py            # SQLAlchemy models (Users, Cases, Alerts, Audit)
│   ├── services/
│   │   ├── sar_generator.py       # LangChain SAR generation + audit extraction
│   │   ├── rag_service.py         # ChromaDB RAG pipeline
│   │   ├── audit_service.py       # Immutable audit trail logging
│   │   └── alert_service.py       # Real-time alert management
│   ├── utils/
│   │   ├── auth.py                # RBAC, authentication, permissions matrix
│   │   └── data_processor.py      # Sample data + data transformation utils
│   └── pages/
│       ├── dashboard.py           # KPI dashboard
│       ├── sar_generator_page.py  # SAR generation UI (from alert or manual)
│       ├── review_approve.py      # Narrative editor + approval workflow
│       ├── case_management.py     # Case list, filters, export
│       ├── alerts_page.py         # Alert centre
│       ├── audit_trail_page.py    # Full audit log viewer
│       ├── analytics_page.py      # Charts and trend analysis
│       └── user_management.py     # Admin user/role management
├── .streamlit/config.toml         # Streamlit theme configuration
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── run.py                         # Quick-start launcher
└── README.md
```

---

## Audit Trail — Why It Matters

The system logs every decision with the following data:

```
=== AI REASONING TRACE ===
Timestamp: 2024-01-15T10:23:45
Model: gpt-4o
Generation time: 8.3s
Tokens used: 3241
Hosting environment: on-premises

--- RISK INDICATORS EXTRACTED ---
  [!] HIGH VALUE: Total transactions of £487,500 exceed £100,000 threshold
  [!] HIGH FREQUENCY: 47 transactions in 7-day monitoring window
  [!] STRUCTURING SUSPECTED: 12 transactions near £10,000 threshold
  [!] INCOME DISPARITY: Transaction volume (487,500) exceeds 2x annual income (85,000)
  [!] MULTIPLE COUNTERPARTIES: 47 distinct counterparties involved

--- TYPOLOGIES MATCHED ---
  [*] FATF Structuring / Smurfing
  [*] Layering through international wire transfers

--- CONFIDENCE LEVEL: HIGH ---

--- RAG CONTEXT USED ---
  Templates: tmpl_structured_layering, tmpl_rapid_movement
  Regulations: reg_poca_2002, reg_jmlsg_guidance, reg_fatf_typologies

--- DATA SOURCES ---
  [>>] Customer KYC profile (CUST-001)
  [>>] Transaction alert (ALT-2024-001)
  [>>] 47 transaction records
```

---

## Security & Compliance

- **Data domain separation**: Customer, Transaction, Fraud, Audit data accessed by role only
- **Password hashing**: bcrypt with 12 rounds
- **Immutable audit logs**: Database records cannot be modified post-creation
- **Tipping-off prevention**: No customer-facing data exposure through the tool
- **Prompt hash logging**: Every LLM call is traceable via SHA-256 prompt hash
- **POCA 2002 / JMLSG / FCA SYSC** guidance embedded in the system prompt and RAG knowledge base

---

## Sample Typologies Covered

1. **STRUCTURING** — 47 transfers from different accounts in 7 days, all near £9,999
2. **HIGH_RISK_JURISDICTION** — PEP customer sending £2.1M through BVI/Cyprus shell companies
3. **RAPID_MOVEMENT** — £350K received and re-sent within 24–48 hours, partial crypto conversion
4. **MULE_ACCOUNT** — Student account receiving £98,500 (8x annual income) with immediate ATM withdrawals
5. **TRADE_BASED_ML** — Invoice values 340% above market rate; payment routed UK → UAE → Nigeria

---

## Regulatory Compliance

| Regulation | Coverage |
|---|---|
| **POCA 2002** | SAR filing obligations, DAML, tipping-off prohibition |
| **JMLSG Guidance** | 5W1H narrative framework, proportionality, objectivity standards |
| **FATF Typologies** | 8 typologies seeded in ChromaDB RAG knowledge base |
| **FCA SYSC** | MLRO responsibilities, record-keeping (5 years), staff training references |
| **AML Red Flags** | 20+ indicators across customer, transaction, account, and counterparty categories |
