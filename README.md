# SAR Guardian — Regulator-Grade SAR Narrative Generator with Immutable Audit Trail

> **Barclays AML Compliance Platform** — AI-assisted Suspicious Activity Report drafting with full machine-auditable reasoning.

---

## Overview

SAR Guardian is a full-stack Financial Crime Compliance application that generates SAR draft narratives powered by a large language model, with complete sentence-level evidence traceability and a tamper-evident audit trail.

### Regulatory Alignment
- **FinCEN** — Financial Crimes Enforcement Network  
- **FIU-IND** — Financial Intelligence Unit – India  
- **FATF** — Financial Action Task Force  

---

## Architecture

| Layer | Technology |
|-------|-----------|
| Compliance UI | Streamlit (deployed on Streamlit Cloud) |
| Backend API | FastAPI, SQLAlchemy (async), Alembic |
| Database | PostgreSQL via Supabase |
| Auth | JWT + bcrypt |
| LLM | Groq (`llama-3.3-70b-versatile`) · OpenAI (`gpt-4o`) fallback |
| RAG | In-memory TF-IDF retrieval (regulatory templates, typology docs) |
| LLM Orchestration | LangChain |
| Next.js Frontend | Next.js 14, TypeScript, TailwindCSS, shadcn/ui |

---

## Features

### Core Capabilities
- **SAR Narrative Generation** — LLM-powered draft narratives from structured case data
- **Sentence-Level Evidence Mapping** — Each narrative sentence maps to transaction IDs, rule triggers, and typologies with SHA-256 hashing
- **Immutable Audit Trail** — Every action logged with hash-chain integrity; fully queryable
- **Override Governance** — Material edits require evidence, reason codes, and supervisor approval for HIGH/CRITICAL severity
- **Role-Based Access Control** — Read-Only, Analyst, Supervisor, Admin with strict data boundaries
- **Alerts Centre** — Real-time alert feed with severity filtering, unread tracking, and mark-as-read

### Compliance Enforcement
- No hallucination — every claim maps to a transaction ID or rule trigger
- No legal conclusions — regulator-safe language only
- No discriminatory language — suspicion based solely on financial behaviour
- Prompt injection prevention in all LLM calls

### Sample Typologies Covered

1. **STRUCTURING** — 47 transfers from different accounts in 7 days, all near ₹9,999
2. **HIGH_RISK_JURISDICTION** — PEP customer sending ₹1.75 Cr through BVI/Cyprus shell companies
3. **RAPID_MOVEMENT** — ₹29L received and re-sent within 24–48 hours, partial crypto conversion
4. **MULE_ACCOUNT** — Student account receiving ₹82L (8x annual income) with immediate ATM withdrawals
5. **TRADE_BASED_ML** — Invoice values 340% above market rate; payment routed India → UAE → Nigeria

---

## Deployed App

The Streamlit compliance UI is deployed at:

**[https://sar-narrative-generator-with-audit-trail.streamlit.app](https://sar-narrative-generator-with-audit-trail.streamlit.app)**

### Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `Admin@2024!` |
| Analyst | `analyst1` | `Analyst@2024!` |
| Supervisor | `supervisor1` | `Supervisor@2024!` |
| Read-Only | `readonly1` | `Readonly@2024!` |

---

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+ (for the Next.js frontend)
- A Groq API key ([console.groq.com](https://console.groq.com)) **or** an OpenAI API key

### Streamlit App (quickest start)

```bash
# 1. Clone the repository
git clone https://github.com/Nandhakishore-NK/SAR-Narrative-Generator-with-Audit-Trail.git
cd SAR-Narrative-Generator-with-Audit-Trail

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the Streamlit app
streamlit run streamlit_app.py
```

Open http://localhost:8501 and log in with any demo credential above.

### FastAPI Backend

```bash
cd backend

# Install backend dependencies
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Seed demo data (optional)
python seed.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

API docs available at http://localhost:8000/docs.

### Next.js Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Frontend available at http://localhost:3000.

---

## Project Structure

```
SAR/
├── streamlit_app.py          # Streamlit compliance UI (Streamlit Cloud)
├── requirements.txt          # Streamlit app dependencies
├── README.md
├── backend/
│   ├── alembic.ini
│   ├── requirements.txt      # FastAPI backend dependencies
│   ├── seed.py
│   ├── alembic/
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── api/
│   │   ├── services/
│   │   ├── middleware/
│   │   ├── prompts/
│   │   └── utils/
│   └── tests/
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.ts
    └── src/
        ├── app/
        ├── components/
        ├── lib/
        ├── hooks/
        └── types/
```

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/login` | JWT authentication | Public |
| POST | `/api/auth/register` | User registration | Admin |
| GET | `/api/cases` | List cases | Analyst+ |
| POST | `/api/cases` | Create case | Analyst+ |
| GET | `/api/cases/{id}` | Get case detail | Analyst+ |
| PATCH | `/api/cases/{id}` | Update case status | Analyst+ |
| POST | `/api/cases/{id}/transactions` | Bulk-add transactions | Analyst+ |
| GET | `/api/cases/{id}/transactions` | List transactions | Analyst+ |
| POST | `/api/cases/{id}/rule-triggers` | Add rule trigger | Analyst+ |
| GET | `/api/cases/{id}/rule-triggers` | List rule triggers | Analyst+ |
| POST | `/api/sar/generate` | Generate SAR narrative | Analyst+ |
| GET | `/api/sar/cases/{id}/narrative` | Get active narrative | Analyst+ |
| GET | `/api/sar/cases/{id}/audit` | SAR generation audit log | Analyst+ |
| POST | `/api/overrides` | Submit override | Analyst+ |
| PATCH | `/api/overrides/{id}/approve` | Approve override | Supervisor+ |
| GET | `/api/overrides/sentence/{id}` | Get overrides for a sentence | Analyst+ |
| GET | `/api/overrides/pending` | List pending approvals | Supervisor+ |
| GET | `/api/audit/{case_id}` | Get audit trail | Supervisor+ |
| GET | `/api/audit/{case_id}/timeline` | Change history | Supervisor+ |

---

## Override Governance Rules

1. **All overrides** require:
   - Valid override reason code
   - Supporting evidence reference
   - Sentence hash comparison

2. **HIGH / CRITICAL severity** additionally require:
   - Supervisor approval before activation
   - Analyst cannot approve their own override

3. **All changes** are:
   - Logged immutably with append-only writes
   - Hash-chain linked to previous record
   - Queryable for full audit history

---

## Security

- JWT token authentication with configurable expiry  
- bcrypt password hashing (12 rounds)  
- Strict CORS policy (configured origins only)  
- Pydantic input validation on all endpoints  
- Prompt injection prevention in LLM calls  
- Case-level data isolation enforced at query level  
- Role-based middleware on every protected route  

---

## Testing

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run a specific module
pytest tests/test_sar_generation.py -v
```

### Test Modules

| File | What it validates |
|------|-------------------|
| `test_sar_generation.py` | Fallback narrative, severity scoring, sentence parsing, data-gap detection |
| `test_hash_integrity.py` | SHA-256 hash chaining on immutable audit log entries |
| `test_override_validation.py` | Override reason codes, evidence requirements, approval workflow |
| `test_role_enforcement.py` | RBAC boundaries — read-only/analyst/supervisor/admin access rules |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL async connection string (Supabase) | — |
| `DATABASE_URL_SYNC` | Synchronous PostgreSQL URL for Alembic migrations | — |
| `SUPABASE_URL` | Supabase project URL | — |
| `JWT_SECRET_KEY` | 256-bit secret for token signing | `replace-with-256-bit-secret` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes | `60` |
| `GROQ_API_KEY` | Groq API key (primary LLM provider) | — |
| `OPENAI_API_KEY` | OpenAI API key (fallback LLM provider) | — |
| `GROQ_MODEL_NAME` | Groq model name | `llama-3.3-70b-versatile` |
| `LLM_MODEL_NAME` | OpenAI model name | `gpt-4` |
| `LLM_TEMPERATURE` | Generation temperature | `0.2` |
| `REDIS_URL` | Redis connection string (for caching) | `redis://redis:6379/0` |
| `APP_ENV` | Deployment environment (`production` hides `/docs`) | `production` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:3000` |

---

## License

Proprietary — Internal Use Only
