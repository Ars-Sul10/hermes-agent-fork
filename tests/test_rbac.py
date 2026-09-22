import pytest

try:
    from integrations.aquera.auth import can, enforce_permission, ROLE_PERMISSIONS
    from integrations.aquera.models import UserContext
    from integrations.aquera.errors import AuthorizationError
except ImportError:
    from hermes.integrations.aquera.auth import can, enforce_permission, ROLE_PERMISSIONS
    from hermes.integrations.aquera.models import UserContext
    from hermes.integrations.aquera.errors import AuthorizationError


def test_viewer_cannot_create_harvest():
    """Requirement Section 25: viewer cannot create harvest."""
    assert not can("viewer", "harvest.create")


def test_admin_can_create_harvest():
    """Requirement Section 25: admin can create harvest."""
    assert can("admin", "harvest.create")


def test_manager_can_create_harvest():
    assert can("manager", "harvest.create")


def test_staff_permissions():
    # Staff can read and create samplings
    assert can("staff", "sampling.read")
    assert can("staff", "sampling.create")
    assert can("staff", "harvest.read")
    # Staff cannot create harvests or manage team
    assert not can("staff", "harvest.create")
    assert not can("staff", "team.manage")


def test_viewer_can_read():
    assert can("viewer", "organization.read")
    assert can("viewer", "pond.read")
    assert can("viewer", "cycle.read")
    assert can("viewer", "sampling.read")
    assert can("viewer", "harvest.read")
    assert can("viewer", "report.read")


def test_none_or_unknown_role():
    assert not can(None, "pond.read")
    assert not can("", "pond.read")
    assert not can("guest", "pond.read")
    assert not can("hacker", "harvest.create")


def test_case_insensitive_role():
    assert can("ADMIN", "harvest.create")
    assert can("Manager", "pond.create")
    assert not can("Viewer", "harvest.create")


def test_enforce_permission_success():
    ctx = UserContext(user_id="usr_123", organization_id="org_abc", role="admin")
    # Should not raise any error
    enforce_permission(ctx, "harvest.create")


def test_enforce_permission_denied():
    ctx = UserContext(user_id="usr_123", organization_id="org_abc", role="viewer")
    with pytest.raises(AuthorizationError) as exc_info:
        enforce_permission(ctx, "harvest.create")
    assert "does not have permission" in str(exc_info.value)


def test_enforce_permission_missing_organization():
    ctx = UserContext(user_id="usr_123", organization_id="", role="admin")
    with pytest.raises(AuthorizationError) as exc_info:
        enforce_permission(ctx, "pond.read")
    assert "Missing organization context" in str(exc_info.value)
