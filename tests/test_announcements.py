import json
import re
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


def _mock_courses_and_announcements(httpx_mock: HTTPXMock, announcements: list):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        json=load_fixture("courses.json"),
    )
    # Announcements endpoint includes context_codes[] query params — match by prefix
    httpx_mock.add_response(
        url=re.compile(re.escape(f"{BASE_URL}/api/v1/announcements")),
        json=announcements,
    )


async def test_announcements_no_filter_returns_all(httpx_mock: HTTPXMock):
    _mock_courses_and_announcements(httpx_mock, load_fixture("announcements.json"))
    from canvas_mcp.tools.announcements import get_announcements
    result = await get_announcements(make_client())
    assert isinstance(result, list)
    assert len(result) == 3


async def test_announcements_keyword_filter(httpx_mock: HTTPXMock):
    _mock_courses_and_announcements(httpx_mock, load_fixture("announcements.json"))
    from canvas_mcp.tools.announcements import get_announcements
    result = await get_announcements(make_client(), keyword="exam")
    assert len(result) == 1
    assert result[0]["title"] == "Exam Review Session Tomorrow"


async def test_announcements_keyword_case_insensitive(httpx_mock: HTTPXMock):
    _mock_courses_and_announcements(httpx_mock, load_fixture("announcements.json"))
    from canvas_mcp.tools.announcements import get_announcements
    result = await get_announcements(make_client(), keyword="EXAM")
    assert len(result) == 1


async def test_announcements_html_stripped(httpx_mock: HTTPXMock):
    _mock_courses_and_announcements(httpx_mock, load_fixture("announcements.json"))
    from canvas_mcp.tools.announcements import get_announcements
    result = await get_announcements(make_client())
    for item in result:
        assert "<" not in item["message"]
        assert ">" not in item["message"]


async def test_announcements_result_shape(httpx_mock: HTTPXMock):
    _mock_courses_and_announcements(httpx_mock, load_fixture("announcements.json"))
    from canvas_mcp.tools.announcements import get_announcements
    result = await get_announcements(make_client())
    for item in result:
        assert "title" in item
        assert "message" in item
        assert "posted_at" in item


async def test_announcements_empty_result(httpx_mock: HTTPXMock):
    _mock_courses_and_announcements(httpx_mock, [])
    from canvas_mcp.tools.announcements import get_announcements
    result = await get_announcements(make_client())
    assert result == []


async def test_announcements_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses", status_code=401)
    from canvas_mcp.tools.announcements import get_announcements
    result = await get_announcements(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 401
