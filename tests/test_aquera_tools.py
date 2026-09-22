import pytest
from unittest.mock import AsyncMock

try:
    from integrations.aquera.tools import AqueraTools
    from integrations.aquera.models import UserContext, HarvestCreate
    from integrations.aquera.errors import AuthorizationError
    from hermes.registry import ToolRegistry
    from hermes.agent import HermesAgent
except ImportError:
    from hermes.integrations.aquera.tools import AqueraTools
    from hermes.integrations.aquera.models import UserContext, HarvestCreate
    from hermes.integrations.aquera.errors import AuthorizationError
    from hermes.hermes.registry import ToolRegistry
    from hermes.hermes.agent import HermesAgent


def test_harvest_create_validation():
    """Requirement Section 21: Validasi harus dilakukan sebelum mutation."""
    # Invalid: biomass <= 0
    with pytest.raises(ValueError, match="total_biomass must be greater than 0"):
        h = HarvestCreate(pond_id="p1", total_biomass=0)
        h.validate()

    with pytest.raises(ValueError, match="total_biomass must be greater than 0"):
        h = HarvestCreate(pond_id="p1", total_biomass=-50)
        h.validate()

    # Invalid: negative price
    with pytest.raises(ValueError, match="price_per_kg cannot be negative"):
        h = HarvestCreate(pond_id="p1", total_biomass=100, price_per_kg=-10)
        h.validate()

    # Invalid: empty pond_id
    with pytest.raises(ValueError, match="pond_id is required"):
        h = HarvestCreate(pond_id="", total_biomass=100)
        h.validate()

    # Valid
    valid_harvest = HarvestCreate(
        pond_id="pond_123",
        total_biomass=500.0,
        price_per_kg=85000.0,
    )
    valid_harvest.validate()


@pytest.mark.asyncio
async def test_tools_pre_execution_authorization_denied():
    """Requirement Section 18: Authorization terjadi sebelum request Aquera."""
    mock_client = AsyncMock()
    tools = AqueraTools(mock_client)

    viewer_context = UserContext(
        user_id="usr_viewer",
        organization_id="org_aquera",
        role="viewer",
    )

    harvest_data = HarvestCreate(pond_id="pond_1", total_biomass=500)

    # Calling create_harvest with viewer role MUST raise AuthorizationError
    with pytest.raises(AuthorizationError) as exc_info:
        await tools.create_harvest(context=viewer_context, harvest_data=harvest_data)

    assert "does not have permission 'harvest.create'" in str(exc_info.value)
    # Ensure no API request was ever dispatched
    assert mock_client.request.call_count == 0


@pytest.mark.asyncio
async def test_tools_pre_execution_authorization_allowed():
    mock_client = AsyncMock()
    mock_client.request.return_value = {"success": True, "message": "Harvest record created"}
    tools = AqueraTools(mock_client)

    admin_context = UserContext(
        user_id="usr_admin",
        organization_id="org_aquera",
        role="admin",
    )

    harvest_data = HarvestCreate(pond_id="pond_1", total_biomass=500)
    res = await tools.create_harvest(context=admin_context, harvest_data=harvest_data)

    assert res["success"] is True
    assert mock_client.request.call_count == 1


@pytest.mark.asyncio
async def test_read_tools_execution():
    mock_client = AsyncMock()
    mock_client.request.return_value = {"success": True, "total": 2, "data": []}
    tools = AqueraTools(mock_client)

    viewer_context = UserContext(
        user_id="usr_viewer",
        organization_id="org_aquera",
        role="viewer",
    )

    # Viewer CAN read ponds, cycles, harvests, reports
    ponds_res = await tools.get_ponds(viewer_context)
    assert ponds_res["success"] is True

    cycles_res = await tools.get_cycles(viewer_context)
    assert cycles_res["success"] is True

    harvests_res = await tools.get_harvests(viewer_context)
    assert harvests_res["success"] is True

    assert mock_client.request.call_count == 3


@pytest.mark.asyncio
async def test_agent_execute_tool_handles_unauthorized_gracefully():
    mock_client = AsyncMock()
    tools = AqueraTools(mock_client)
    registry = ToolRegistry()
    registry.register(tools.create_harvest, name="create_harvest", requires_context=True)

    agent = HermesAgent(registry=registry)
    viewer_context = UserContext(
        user_id="usr_viewer",
        organization_id="org_aquera",
        role="viewer",
    )

    result = await agent.execute_tool(
        tool_name="create_harvest",
        arguments={"pond_id": "p1", "total_biomass": 100},
        context=viewer_context,
    )

    assert "error" in result
    assert "Authorization denied" in result["error"]
