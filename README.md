# SAR Guardian — Regulator-Grade SAR Narrative Generator with Immutable Audit Trail

## Overview

SAR Guardian is a production-ready, full-stack Financial Crime Compliance application that generates Suspicious Activity Report (SAR) draft narratives with complete machine-auditable reasoning records.

### Regulatory Alignment
- **FinCEN** — Financial Crimes Enforcement Network
- **FIU-IND** — Financial Intelligence Unit – India
- **FATF** — Financial Action Task Force

---

## Architecture

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy, Alembic, LangChain, Pydantic |
| Frontend | Next.js 14 (App Router), TypeScript, TailwindCSS, shadcn/ui |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Vector Store | ChromaDB |
| Auth | JWT + bcrypt |
| Containerization | Docker + docker-compose |

---

## Features

### Core Capabilities
- **SAR Narrative Generation** — LLM-powered draft narratives from structured case data
- **Immutable Audit Trail** — Every action logged with hash-chain integrity
- **Sentence-Level Evidence Mapping** — Each narrative sentence maps to transaction IDs, rule triggers, and typologies
- **Override Governance** — Material edits require evidence, reason codes, and supervisor approval for HIGH/CRITICAL severity
- **Role-Based Access Control** — Analyst, Supervisor, Admin with strict data boundaries
- **RAG Integration** — Regulatory template retrieval via ChromaDB

### Compliance Enforcement
- No hallucination policy — every claim maps to evidence
- No legal conclusions — regulator-safe language only
- No discriminatory language — suspicion based solely on financial behavior
- No cross-case data leakage
- Prompt injection prevention

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key (or Bedrock-compatible endpoint)

### Setup

```bash
# 1. Clone the repository
git clone <repo-url> && cd SAR

# 2. Copy environment variables
cp .env.example .env

# 3. Edit .env with your API keys and secrets
# IMPORTANT: Change JWT_SECRET_KEY and POSTGRES_PASSWORD

# 4. Start all services
docker-compose up --build -d

# 5. Seed demo data (optional)
docker-compose exec backend python seed.py

# 6. Open the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

### Default Demo Users (after seeding)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@sarguardian.com | Admin@123 |
| Supervisor | supervisor@sarguardian.com | Super@123 |
| Analyst | analyst@sarguardian.com | Analyst@123 |

---

## Project Structure

```
SAR/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
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
│   ├── tests/
│   └── seed.py
└── frontend/
    ├── Dockerfile
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
| POST | /api/auth/login | JWT authentication | Public |
| POST | /api/auth/register | User registration | Admin |
| GET | /api/cases | List cases | Analyst+ |
| POST | /api/cases | Create case | Analyst+ |
| GET | /api/cases/{id} | Get case detail | Analyst+ |
| POST | /api/cases/{id}/transactions | Add transactions | Analyst+ |
| POST | /api/cases/{id}/generate-sar | Generate SAR narrative | Analyst+ |
| GET | /api/cases/{id}/narrative | Get active narrative | Analyst+ |
| POST | /api/overrides | Submit override | Analyst+ |
| PATCH | /api/overrides/{id}/approve | Approve override | Supervisor+ |
| GET | /api/audit/{case_id} | Get audit trail | Supervisor+ |
| GET | /api/audit/{case_id}/timeline | Change history | Supervisor+ |

---

## Override Governance Rules

1. **All overrides** require:
   - Valid override reason code
   - Supporting evidence reference
   - Sentence hash comparison

2. **HIGH/CRITICAL severity** additionally require:
   - Supervisor approval before activation
   - Analyst cannot approve own override

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
# Run backend tests
docker-compose exec backend pytest tests/ -v

# Run specific test module
docker-compose exec backend pytest tests/test_sar_generation.py -v
```

---

## Environment Variables

See `.env.example` for all required configuration. Critical variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string |
| `JWT_SECRET_KEY` | 256-bit secret for token signing |
| `OPENAI_API_KEY` | LLM provider API key |
| `LLM_MODEL_NAME` | Model identifier (gpt-4, etc.) |
| `LLM_TEMPERATURE` | Generation temperature (0.2 recommended) |
| `CORS_ORIGINS` | Allowed frontend origins |

---

## License

Proprietary — Internal Use Only
