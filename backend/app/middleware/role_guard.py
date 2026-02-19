"""
Role Guard Middleware — JWT authentication and role-based access control.

Provides FastAPI dependencies for:
- Token extraction and validation
- Current user resolution
- Role-based endpoint protection

Security notes:
- Token must be in Authorization: Bearer <token> header
- User must be active to access any protected endpoint
- Role checks are hierarchical: admin > supervisor > analyst
"""

from typing import List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import decode_access_token, get_user_by_id

# HTTP Bearer token extractor
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate JWT token, return the authenticated user.
    Raises 401 if token is invalid or user is inactive.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload invalid",
        )

    try:
        user = await get_user_by_id(db, UUID(user_id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier in token",
        )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def require_roles(*allowed_roles: UserRole):
    """
    Factory for role-based access dependencies.
    
    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_roles(UserRole.admin))])
        
    Or inject the user:
        current_user: User = Depends(require_roles(UserRole.supervisor, UserRole.admin))
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {', '.join(r.value for r in allowed_roles)}",
            )
        return current_user
    return role_checker


# Convenience dependencies for common role checks
require_analyst = require_roles(UserRole.analyst, UserRole.supervisor, UserRole.admin)
require_supervisor = require_roles(UserRole.supervisor, UserRole.admin)
require_admin = require_roles(UserRole.admin)
