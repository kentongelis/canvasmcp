import httpx
import pytest
from pytest_httpx import HTTPXMock
from canvas_mcp.canvas_client import CanvasClient


BASE_URL = "https://canvas.example.com"
TOKEN = "test-token-abc"


# --- Init + successful get() ---

async def test_client_sets_bearer_header(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        json=[{"id": 1, "name": "Test Course"}],
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    request = httpx_mock.get_requests()[0]
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert result == [{"id": 1, "name": "Test Course"}]


async def test_client_returns_parsed_json(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        json={"key": "value"},
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    assert result == {"key": "value"}


# --- Error handling: 401, 404, 429 ---

async def test_client_401_returns_error_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        status_code=401,
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    assert isinstance(result, dict)
    assert result["error"] == 401
    assert "token" in result["message"].lower() or "unauthorized" in result["message"].lower()


async def test_client_404_returns_error_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        status_code=404,
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    assert isinstance(result, dict)
    assert result["error"] == 404
    assert "not found" in result["message"].lower()


async def test_client_429_returns_error_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        status_code=429,
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    assert isinstance(result, dict)
    assert result["error"] == 429
    assert "rate limit" in result["message"].lower()



# --- Error handling: other statuses, network, config ---

async def test_client_403_returns_error_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        status_code=403,
        text='{"status": "unauthorized"}',
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    assert result["error"] == 403
    assert "forbidden" in result["message"].lower()


async def test_client_403_rate_limit_reported_as_rate_limit(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        status_code=403,
        text="403 Forbidden (Rate Limit Exceeded)",
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    assert result["error"] == 403
    assert "rate limit" in result["message"].lower()


async def test_client_500_returns_error_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        status_code=500,
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    assert result["error"] == 500
    assert "server error" in result["message"].lower()


async def test_client_unlisted_4xx_returns_error_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        status_code=422,
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    assert result["error"] == 422
    assert "422" in result["message"]


async def test_client_connection_error_returns_error_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(httpx.ConnectError("boom"))
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    assert result["error"] == "connection"
    assert "could not reach canvas" in result["message"].lower()


async def test_client_timeout_returns_error_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(httpx.ReadTimeout("slow"))
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get_all_pages("/courses")
    assert result["error"] == "connection"


async def test_client_non_json_response_returns_error_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        text="<html>Log in to Canvas</html>",
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get("/courses")
    assert result["error"] == "invalid_response"


async def test_client_missing_base_url_returns_config_error(monkeypatch):
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    client = CanvasClient(token=TOKEN)
    result = await client.get("/courses")
    assert result["error"] == "config"
    assert "CANVAS_BASE_URL" in result["message"]


async def test_client_missing_token_returns_config_error(monkeypatch):
    monkeypatch.delenv("CANVAS_API_TOKEN", raising=False)
    client = CanvasClient(base_url=BASE_URL)
    result = await client.get_all_pages("/courses")
    assert result["error"] == "config"
    assert "CANVAS_API_TOKEN" in result["message"]


# --- Pagination ---

async def test_get_all_pages_follows_link_header(httpx_mock: HTTPXMock):
    page2_url = f"{BASE_URL}/api/v1/courses?page=2"
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses?per_page=100",
        json=[{"id": 1}],
        headers={"Link": f'<{page2_url}>; rel="next"'},
    )
    httpx_mock.add_response(
        url=page2_url,
        json=[{"id": 2}],
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get_all_pages("/courses")
    assert result == [{"id": 1}, {"id": 2}]


async def test_get_all_pages_no_next_link(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses?per_page=100",
        json=[{"id": 1}, {"id": 2}],
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get_all_pages("/courses")
    assert result == [{"id": 1}, {"id": 2}]


async def test_get_all_pages_error_on_later_page(httpx_mock: HTTPXMock):
    page2_url = f"{BASE_URL}/api/v1/courses?page=2"
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses?per_page=100",
        json=[{"id": 1}],
        headers={"Link": f'<{page2_url}>; rel="next"'},
    )
    httpx_mock.add_response(url=page2_url, status_code=500)
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get_all_pages("/courses")
    assert result["error"] == 500
