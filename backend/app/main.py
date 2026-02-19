"""
SAR Guardian — FastAPI Application Entry Point

Production-ready ASGI application with:
- CORS middleware (strict origins)
- JWT authentication
- Role-based access control
- Async PostgreSQL connections
- Structured logging
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, cases, transactions, sar_generation, overrides, audit


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup: auto-create tables (for SQLite local dev)
    from app.database import engine, Base
    # Import all models so Base.metadata knows about them
    from app.models import (  # noqa: F401
        user, case, transaction, rule_trigger,
        sar_narrative, narrative_sentence, audit_trail,
        override, immutable_log,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: cleanup resources


app = FastAPI(
    title="SAR Guardian",
    description="Regulator-Grade SAR Narrative Generator with Immutable Audit Trail",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)

# ------- CORS — Strict origin policy -------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# ------- API Route Registration -------
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(sar_generation.router, prefix="/api/sar", tags=["SAR Generation"])
app.include_router(overrides.router, prefix="/api/overrides", tags=["Overrides"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit Trail"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers and orchestrators."""
    return {"status": "healthy", "service": "sar-guardian-backend"}
