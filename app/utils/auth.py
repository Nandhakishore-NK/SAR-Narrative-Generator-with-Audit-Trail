"""
Authentication & Role-Based Access Control (RBAC) Module.
Implements role-based permissions to prevent data leakage across domain boundaries.
"""
import bcrypt
import logging
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.models.database import User, UserRole, SessionLocal

logger = logging.getLogger(__name__)

# ===== PERMISSIONS MATRIX =====
# Maps roles to allowed actions - prevents data leakage across domain boundaries
PERMISSIONS: Dict[str, List[str]] = {
    UserRole.ADMIN: [
        "view_all_cases", "create_case", "edit_case", "delete_case",
        "generate_sar", "edit_narrative", "approve_sar", "reject_sar", "file_sar",
        "view_customer_data", "view_transaction_data", "view_fraud_data",
        "view_audit_logs", "export_data", "manage_users", "view_alerts",
        "acknowledge_alerts", "view_reports", "configure_system"
    ],
    UserRole.SUPERVISOR: [
        "view_all_cases", "create_case", "edit_case",
        "generate_sar", "edit_narrative", "approve_sar", "reject_sar", "file_sar",
        "view_customer_data", "view_transaction_data",
        "view_audit_logs", "export_data", "view_alerts", "acknowledge_alerts",
        "view_reports"
    ],
    UserRole.ANALYST: [
        "view_assigned_cases", "create_case",
        "generate_sar", "edit_narrative",
        "view_customer_data", "view_transaction_data",
        "view_alerts", "view_reports"
    ],
    UserRole.READ_ONLY: [
        "view_assigned_cases",
        "view_customer_data",
        "view_reports"
    ]
}

# Domain boundary enforcement: which roles can access which data domains
DATA_DOMAIN_ACCESS: Dict[str, List[str]] = {
    "customer": [UserRole.ANALYST, UserRole.SUPERVISOR, UserRole.ADMIN],
    "transaction": [UserRole.ANALYST, UserRole.SUPERVISOR, UserRole.ADMIN],
    "fraud": [UserRole.SUPERVISOR, UserRole.ADMIN],       # Restricted domain
    "audit": [UserRole.SUPERVISOR, UserRole.ADMIN],
    "system": [UserRole.ADMIN]
}


def hash_password(plain_password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def has_permission(user_role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    role_key = UserRole(user_role) if isinstance(user_role, str) else user_role
    allowed = PERMISSIONS.get(role_key, [])
    return permission in allowed


def can_access_domain(user_role: str, domain: str) -> bool:
    """Check if a role can access a specific data domain (prevents cross-domain data leakage)."""
    role_key = UserRole(user_role) if isinstance(user_role, str) else user_role
    allowed_roles = DATA_DOMAIN_ACCESS.get(domain.lower(), [])
    return role_key in allowed_roles


def get_user_by_username(username: str) -> Optional[User]:
    """Retrieve a user by username."""
    db: Session = SessionLocal()
    try:
        return db.query(User).filter(User.username == username, User.is_active == True).first()
    finally:
        db.close()


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user and update last login."""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username, User.is_active == True).first()
        if user and verify_password(password, user.hashed_password):
            user.last_login = datetime.utcnow()
            db.commit()
            return user
        return None
    finally:
        db.close()


def create_user(
    username: str,
    email: str,
    full_name: str,
    password: str,
    role: str = "ANALYST",
    department: str = "AML Compliance"
) -> Optional[User]:
    """Create a new user."""
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            return None
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole(role),
            department=department,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        logger.error(f"User creation failed: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def get_all_users() -> List[User]:
    """Get all active users."""
    db: Session = SessionLocal()
    try:
        return db.query(User).filter(User.is_active == True).all()
    finally:
        db.close()


def seed_default_users():
    """Seed default users if none exist."""
    db: Session = SessionLocal()
    try:
        count = db.query(User).count()
        if count == 0:
            defaults = [
                {
                    "username": "admin",
                    "email": "admin@barclays.com",
                    "full_name": "System Administrator",
                    "password": "Admin@2024!",
                    "role": "ADMIN",
                    "department": "IT Security"
                },
                {
                    "username": "analyst1",
                    "email": "analyst1@barclays.com",
                    "full_name": "Sarah Johnson",
                    "password": "Analyst@2024!",
                    "role": "ANALYST",
                    "department": "AML Compliance"
                },
                {
                    "username": "supervisor1",
                    "email": "supervisor1@barclays.com",
                    "full_name": "David Chen",
                    "password": "Supervisor@2024!",
                    "role": "SUPERVISOR",
                    "department": "AML Compliance"
                },
                {
                    "username": "readonly1",
                    "email": "readonly1@barclays.com",
                    "full_name": "Emma Williams",
                    "password": "Readonly@2024!",
                    "role": "READ_ONLY",
                    "department": "Internal Audit"
                }
            ]
            for u in defaults:
                user = User(
                    username=u["username"],
                    email=u["email"],
                    full_name=u["full_name"],
                    hashed_password=hash_password(u["password"]),
                    role=UserRole(u["role"]),
                    department=u["department"],
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.add(user)
            db.commit()
            logger.info("Default users seeded successfully.")
    except Exception as e:
        logger.error(f"Failed to seed default users: {e}")
        db.rollback()
    finally:
        db.close()


ROLE_COLORS = {
    "ADMIN": "#e74c3c",
    "SUPERVISOR": "#e67e22",
    "ANALYST": "#3498db",
    "READ_ONLY": "#95a5a6"
}

ROLE_DESCRIPTIONS = {
    "ADMIN": "Full system access including user management and configuration",
    "SUPERVISOR": "Can approve/reject SARs, view all cases, export data",
    "ANALYST": "Can create cases, generate and edit SAR narratives",
    "READ_ONLY": "View-only access to assigned cases and reports"
}
