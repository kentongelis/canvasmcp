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


# --- Pagination ---

async def test_get_all_pages_follows_link_header(httpx_mock: HTTPXMock):
    page2_url = f"{BASE_URL}/api/v1/courses?page=2"
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
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
        url=f"{BASE_URL}/api/v1/courses",
        json=[{"id": 1}, {"id": 2}],
    )
    client = CanvasClient(base_url=BASE_URL, token=TOKEN)
    result = await client.get_all_pages("/courses")
    assert result == [{"id": 1}, {"id": 2}]
