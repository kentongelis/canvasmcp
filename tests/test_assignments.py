import json
import pytest
from pathlib import Path
from pytest_httpx import HTTPXMock
from canvas_mcp.canvas_client import CanvasClient

BASE_URL = "https://canvas.example.com"
TOKEN = "test-token-abc"

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def make_client() -> CanvasClient:
    return CanvasClient(base_url=BASE_URL, token=TOKEN)


# ---------------------------------------------------------------------------
# list_courses
# ---------------------------------------------------------------------------

async def test_list_courses_returns_only_active(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        json=load_fixture("courses.json"),
    )
    from canvas_mcp.tools.assignments import list_courses
    result = await list_courses(make_client())
    assert isinstance(result, list)
    ids = [c["id"] for c in result]
    assert 101 in ids
    assert 102 in ids
    assert 103 not in ids  # completed — must be excluded


async def test_list_courses_shape(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        json=load_fixture("courses.json"),
    )
    from canvas_mcp.tools.assignments import list_courses
    result = await list_courses(make_client())
    for course in result:
        assert "id" in course
        assert "name" in course


async def test_list_courses_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        status_code=401,
    )
    from canvas_mcp.tools.assignments import list_courses
    result = await list_courses(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 401
