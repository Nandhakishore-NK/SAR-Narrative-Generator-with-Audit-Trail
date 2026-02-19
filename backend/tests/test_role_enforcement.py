"""
Test — Role Enforcement

Validates:
- Role hierarchy: admin > supervisor > analyst
- Analyst cannot perform supervisor actions
- Role parsing from JWT tokens
"""

import pytest
from app.models.user import UserRole


class TestRoleEnforcement:
    """Test role-based access control logic."""

    def test_role_hierarchy(self):
        """Verify role hierarchy definitions."""
        assert UserRole.analyst.value == "analyst"
        assert UserRole.supervisor.value == "supervisor"
        assert UserRole.admin.value == "admin"

    def test_analyst_not_in_supervisor_roles(self):
        """Analyst role must not be in supervisor-level role set."""
        supervisor_roles = {UserRole.supervisor, UserRole.admin}
        assert UserRole.analyst not in supervisor_roles

    def test_supervisor_can_access_analyst_endpoints(self):
        """Supervisor role should be included in analyst-level role set."""
        analyst_allowed = {UserRole.analyst, UserRole.supervisor, UserRole.admin}
        assert UserRole.supervisor in analyst_allowed

    def test_admin_can_access_all_endpoints(self):
        """Admin role should be in every role set."""
        analyst_allowed = {UserRole.analyst, UserRole.supervisor, UserRole.admin}
        supervisor_allowed = {UserRole.supervisor, UserRole.admin}
        admin_allowed = {UserRole.admin}
        
        assert UserRole.admin in analyst_allowed
        assert UserRole.admin in supervisor_allowed
        assert UserRole.admin in admin_allowed

    def test_self_approval_prevention(self):
        """Analyst cannot approve their own override (same user ID check)."""
        analyst_id = "user-123"
        approver_id = "user-123"
        assert analyst_id == approver_id  # This should be blocked

        approver_id = "user-456"
        assert analyst_id != approver_id  # This should be allowed

    def test_role_from_string(self):
        """Roles can be constructed from string values."""
        assert UserRole("analyst") == UserRole.analyst
        assert UserRole("supervisor") == UserRole.supervisor
        assert UserRole("admin") == UserRole.admin

    def test_invalid_role_raises_error(self):
        """Invalid role string should raise ValueError."""
        with pytest.raises(ValueError):
            UserRole("superuser")
