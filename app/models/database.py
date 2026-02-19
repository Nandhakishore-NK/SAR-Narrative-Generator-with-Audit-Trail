"""SAR System - SQLAlchemy Database Models"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    Float, Boolean, JSON, ForeignKey, Enum as SAEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings

Base = declarative_base()
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


class CaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    FILED = "FILED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class UserRole(str, enum.Enum):
    ANALYST = "ANALYST"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"
    READ_ONLY = "READ_ONLY"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False)
    full_name = Column(String(200), nullable=False)
    hashed_password = Column(String(500), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.ANALYST, nullable=False)
    department = Column(String(100), default="AML Compliance")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    cases = relationship("SARCase", back_populates="assigned_analyst")
    audit_logs = relationship("AuditLog", back_populates="user")


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    date_of_birth = Column(String(20), nullable=True)
    nationality = Column(String(100), nullable=True)
    id_type = Column(String(50), nullable=True)
    id_number = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    occupation = Column(String(200), nullable=True)
    employer = Column(String(200), nullable=True)
    annual_income = Column(Float, nullable=True)
    risk_rating = Column(String(20), default="MEDIUM")
    kyc_status = Column(String(50), default="VERIFIED")
    kyc_date = Column(DateTime, nullable=True)
    pep_status = Column(Boolean, default=False)
    sanctions_checked = Column(Boolean, default=True)
    account_opening_date = Column(DateTime, nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    country = Column(String(100), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    cases = relationship("SARCase", back_populates="customer")


class TransactionAlert(Base):
    __tablename__ = "transaction_alerts"
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customer_profiles.customer_id"), nullable=False)
    alert_type = Column(String(100), nullable=False)
    alert_rule = Column(String(200), nullable=True)
    severity = Column(SAEnum(AlertSeverity), default=AlertSeverity.MEDIUM)
    transaction_data = Column(JSON, nullable=True)
    total_amount = Column(Float, nullable=True)
    transaction_count = Column(Integer, default=0)
    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)
    counterparties = Column(JSON, nullable=True)
    jurisdictions_involved = Column(JSON, nullable=True)
    alert_score = Column(Float, nullable=True)
    status = Column(String(50), default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)
    triggering_factors = Column(JSON, nullable=True)
    case = relationship("SARCase", back_populates="alert", uselist=False)


class SARCase(Base):
    __tablename__ = "sar_cases"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(50), unique=True, nullable=False, index=True)
    alert_id = Column(String(50), ForeignKey("transaction_alerts.alert_id"), nullable=True)
    customer_id = Column(String(50), ForeignKey("customer_profiles.customer_id"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SAEnum(CaseStatus), default=CaseStatus.OPEN)
    priority = Column(String(20), default="MEDIUM")
    # SAR Narrative
    generated_narrative = Column(Text, nullable=True)
    edited_narrative = Column(Text, nullable=True)
    final_narrative = Column(Text, nullable=True)
    narrative_version = Column(Integer, default=0)
    # Metadata
    suspicion_typology = Column(String(200), nullable=True)
    reporting_entity = Column(String(200), default="Barclays Bank PLC")
    filing_jurisdiction = Column(String(100), default="UK")
    sar_reference = Column(String(100), nullable=True)
    # Audit
    generation_metadata = Column(JSON, nullable=True)
    rag_sources_used = Column(JSON, nullable=True)
    analyst_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    filed_at = Column(DateTime, nullable=True)
    approved_by = Column(String(100), nullable=True)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships
    customer = relationship("CustomerProfile", back_populates="cases")
    alert = relationship("TransactionAlert", back_populates="case")
    assigned_analyst = relationship("User", back_populates="cases")
    audit_logs = relationship("AuditLog", back_populates="case")
    narrative_versions = relationship("NarrativeVersion", back_populates="case")


class NarrativeVersion(Base):
    __tablename__ = "narrative_versions"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(50), ForeignKey("sar_cases.case_id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    narrative_text = Column(Text, nullable=False)
    change_summary = Column(Text, nullable=True)
    changed_by = Column(String(100), nullable=True)
    change_type = Column(String(50), default="EDIT")  # GENERATED | EDIT | APPROVED
    created_at = Column(DateTime, default=datetime.utcnow)
    case = relationship("SARCase", back_populates="narrative_versions")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(50), ForeignKey("sar_cases.case_id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(200), nullable=False)
    action_category = Column(String(100), nullable=True)  # GENERATION | EDIT | APPROVAL | ACCESS | ALERT
    details = Column(JSON, nullable=True)
    reasoning_trace = Column(Text, nullable=True)
    data_sources_used = Column(JSON, nullable=True)
    rules_matched = Column(JSON, nullable=True)
    llm_prompt_hash = Column(String(64), nullable=True)
    llm_model_used = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    case = relationship("SARCase", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")


class SystemAlert(Base):
    __tablename__ = "system_alerts"
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(100), nullable=False)
    severity = Column(SAEnum(AlertSeverity), default=AlertSeverity.MEDIUM)
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)
    case_id = Column(String(50), nullable=True)
    customer_id = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False)
    sent_via_email = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
