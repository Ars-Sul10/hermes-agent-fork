from __future__ import annotations
from typing import Optional, Set, Dict
from .models import UserContext
from .errors import AuthorizationError

# Centralized RBAC definition aligned with Aquera database roles:
# ('owner', 'admin', 'manager', 'staff', 'viewer')
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "owner": {
        "organization.read",
        "organization.update",
        "team.read",
        "team.manage",
        "farm_site.read",
        "farm_site.create",
        "pond.read",
        "pond.create",
        "cycle.read",
        "cycle.create",
        "sampling.read",
        "sampling.create",
        "harvest.read",
        "harvest.create",
        "report.read",
        "feed.read",
        "feed.create",
        "invoice.read",
        "invoice.create",
    },
    "admin": {
        "organization.read",
        "team.read",
        "farm_site.read",
        "farm_site.create",
        "pond.read",
        "pond.create",
        "cycle.read",
        "cycle.create",
        "sampling.read",
        "sampling.create",
        "harvest.read",
        "harvest.create",
        "report.read",
        "feed.read",
        "feed.create",
        "invoice.read",
        "invoice.create",
    },
    "manager": {
        "organization.read",
        "team.read",
        "farm_site.read",
        "farm_site.create",
        "pond.read",
        "pond.create",
        "cycle.read",
        "cycle.create",
        "sampling.read",
        "sampling.create",
        "harvest.read",
        "harvest.create",
        "report.read",
        "feed.read",
        "feed.create",
        "invoice.read",
    },
    "staff": {
        "organization.read",
        "team.read",
        "farm_site.read",
        "pond.read",
        "cycle.read",
        "sampling.read",
        "sampling.create",
        "harvest.read",
        "report.read",
        "feed.read",
        "feed.create",
    },
    "viewer": {
        "organization.read",
        "team.read",
        "farm_site.read",
        "pond.read",
        "cycle.read",
        "sampling.read",
        "harvest.read",
        "report.read",
        "feed.read",
        "invoice.read",
    },
}


def can(role: Optional[str], permission: str) -> bool:
    """Evaluate whether a given role holds the requested permission.
    Returns False if role is None or invalid."""
    if not role:
        return False
    return permission in ROLE_PERMISSIONS.get(role.lower(), set())


def enforce_permission(context: UserContext, permission: str) -> None:
    """Enforce authorization before tool execution.
    Raises AuthorizationError if permission is denied."""
    if not context.organization_id:
        raise AuthorizationError("Missing organization context. Access denied.")

    if not can(context.role, permission):
        raise AuthorizationError(
            f"Role '{context.role}' does not have permission '{permission}'."
        )
