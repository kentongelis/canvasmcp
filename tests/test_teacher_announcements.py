import json
import re
from pathlib import Path
from pytest_httpx import HTTPXMock
from canvas_mcp.canvas_client import CanvasClient

BASE_URL = "https://canvas.example.com"
TOKEN = "test-token-abc"
FIXTURES = Path(__file__).parent / "fixtures"

TEACHING_COURSES_URL = (
    f"{BASE_URL}/api/v1/courses?enrollment_type=teacher&enrollment_state=active&per_page=100"
)


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def make_client() -> CanvasClient:
    return CanvasClient(base_url=BASE_URL, token=TOKEN)


def _mock_teaching_courses_and_announcements(httpx_mock: HTTPXMock, announcements: list):
    httpx_mock.add_response(url=TEACHING_COURSES_URL, json=load_fixture("teacher_courses.json"))
    # Announcements endpoint includes context_codes[] query params — match by prefix
    httpx_mock.add_response(
        url=re.compile(re.escape(f"{BASE_URL}/api/v1/announcements")),
        json=announcements,
    )


async def test_teaching_announcements_no_filter_returns_all(httpx_mock: HTTPXMock):
    _mock_teaching_courses_and_announcements(httpx_mock, load_fixture("announcements.json"))
    from canvas_mcp.tools.teacher_announcements import get_teaching_announcements
    result = await get_teaching_announcements(make_client())
    assert isinstance(result, list)
    assert len(result) == 3


async def test_teaching_announcements_uses_only_active_teaching_courses(httpx_mock: HTTPXMock):
    _mock_teaching_courses_and_announcements(httpx_mock, [])
    from canvas_mcp.tools.teacher_announcements import get_teaching_announcements
    await get_teaching_announcements(make_client())
    request = httpx_mock.get_requests(url=re.compile(re.escape(f"{BASE_URL}/api/v1/announcements")))[0]
    # The concluded course 203 is left out
    assert request.url.params.get_list("context_codes[]") == ["course_201", "course_202"]


async def test_teaching_announcements_keyword_filter(httpx_mock: HTTPXMock):
    _mock_teaching_courses_and_announcements(httpx_mock, load_fixture("announcements.json"))
    from canvas_mcp.tools.teacher_announcements import get_teaching_announcements
    result = await get_teaching_announcements(make_client(), keyword="EXAM")
    assert len(result) == 1
    assert result[0]["title"] == "Exam Review Session Tomorrow"


async def test_teaching_announcements_html_stripped_and_shape(httpx_mock: HTTPXMock):
    _mock_teaching_courses_and_announcements(httpx_mock, load_fixture("announcements.json"))
    from canvas_mcp.tools.teacher_announcements import get_teaching_announcements
    result = await get_teaching_announcements(make_client())
    for item in result:
        assert set(item) == {"title", "message", "posted_at"}
        assert "<" not in item["message"]
        assert ">" not in item["message"]


async def test_teaching_announcements_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=TEACHING_COURSES_URL, status_code=401)
    from canvas_mcp.tools.teacher_announcements import get_teaching_announcements
    result = await get_teaching_announcements(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 401
