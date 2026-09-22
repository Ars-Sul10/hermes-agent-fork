import pytest
from unittest.mock import patch, AsyncMock
import httpx

try:
    from integrations.aquera.client import AqueraClient
    from integrations.aquera.errors import (
        AqueraError,
        AuthenticationError,
        AuthorizationError,
        NotFoundError,
        ValidationError,
        RateLimitError,
        ServerError,
        map_http_status_to_error,
    )
except ImportError:
    from hermes.integrations.aquera.client import AqueraClient
    from hermes.integrations.aquera.errors import (
        AqueraError,
        AuthenticationError,
        AuthorizationError,
        NotFoundError,
        ValidationError,
        RateLimitError,
        ServerError,
        map_http_status_to_error,
    )


def test_client_init_and_headers():
    client = AqueraClient(
        base_url="https://api.aquera.id/",
        token="test-secret-token",
        timeout=15.0,
        max_retries=2,
    )
    assert client.base_url == "https://api.aquera.id"
    assert client.token == "test-secret-token"
    assert client.timeout == 15.0
    assert client.max_retries == 2

    headers = client._headers(
        organization_id="org_test_123",
        user_id="usr_abc",
        request_id="req-999",
    )
    assert headers["Authorization"] == "Bearer test-secret-token"
    assert headers["x-organization-id"] == "org_test_123"
    assert headers["x-user-id"] == "usr_abc"
    assert headers["x-request-id"] == "req-999"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"


def test_error_mapping():
    err_401 = map_http_status_to_error(401, "Invalid token")
    assert isinstance(err_401, AuthenticationError)

    err_403 = map_http_status_to_error(403, "Forbidden")
    assert isinstance(err_403, AuthorizationError)

    err_404 = map_http_status_to_error(404, "Pond not found")
    assert isinstance(err_404, NotFoundError)

    err_422 = map_http_status_to_error(422, "Invalid biomass value")
    assert isinstance(err_422, ValidationError)

    err_429 = map_http_status_to_error(429, "Too many requests")
    assert isinstance(err_429, RateLimitError)

    err_500 = map_http_status_to_error(500, "Internal database error")
    assert isinstance(err_500, ServerError)


@pytest.mark.asyncio
async def test_successful_get_request():
    client = AqueraClient(base_url="http://test-aquera.local", token="dummy")

    mock_resp = httpx.Response(
        status_code=200,
        content=b'{"success": true, "data": [{"id": "p1", "name": "Kolam A"}]}',
        request=httpx.Request("GET", "http://test-aquera.local/api/v1/ponds"),
    )

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resp
        res = await client.request("GET", "/api/v1/ponds", organization_id="org1")
        assert res["success"] is True
        assert res["data"][0]["name"] == "Kolam A"


@pytest.mark.asyncio
async def test_authentication_error_raised():
    client = AqueraClient(base_url="http://test-aquera.local", token="bad-token")

    mock_resp = httpx.Response(
        status_code=401,
        content=b'{"error": "Unauthorized"}',
        request=httpx.Request("GET", "http://test-aquera.local/api/v1/ponds"),
    )

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resp
        with pytest.raises(AuthenticationError):
            await client.request("GET", "/api/v1/ponds", organization_id="org1")


@pytest.mark.asyncio
async def test_post_mutation_no_blind_retry():
    """Requirement Section 10: Jangan melakukan retry sembarangan terhadap operasi mutation."""
    client = AqueraClient(base_url="http://test-aquera.local", token="dummy", max_retries=3)

    mock_resp = httpx.Response(
        status_code=500,
        content=b'{"error": "Server error on insert"}',
        request=httpx.Request("POST", "http://test-aquera.local/api/v1/harvest"),
    )

    with patch.object(httpx.AsyncClient, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resp
        with pytest.raises(ServerError):
            await client.request("POST", "/api/v1/harvest", json_data={"total_biomass": 100})
        # Verify request was called only ONCE (no retry on POST mutations)
        assert mock_req.call_count == 1
