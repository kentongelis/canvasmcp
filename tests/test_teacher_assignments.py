import json
from pathlib import Path
from pytest_httpx import HTTPXMock
from canvas_mcp.canvas_client import CanvasClient

BASE_URL = "https://canvas.example.com"
TOKEN = "test-token-abc"

FIXTURES = Path(__file__).parent / "fixtures"

TEACHING_COURSES_URL = (
    f"{BASE_URL}/api/v1/courses?enrollment_type=teacher&enrollment_state=active"
)


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def make_client() -> CanvasClient:
    return CanvasClient(base_url=BASE_URL, token=TOKEN)


# ---------------------------------------------------------------------------
# list_teaching_courses
# ---------------------------------------------------------------------------

async def test_list_teaching_courses_returns_only_active(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=TEACHING_COURSES_URL,
        json=load_fixture("teacher_courses.json"),
    )
    from canvas_mcp.tools.teacher_assignments import list_teaching_courses
    result = await list_teaching_courses(make_client())
    assert isinstance(result, list)
    ids = [c["id"] for c in result]
    assert 201 in ids
    assert 202 in ids
    assert 203 not in ids  # completed — must be excluded


async def test_list_teaching_courses_shape(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=TEACHING_COURSES_URL,
        json=load_fixture("teacher_courses.json"),
    )
    from canvas_mcp.tools.teacher_assignments import list_teaching_courses
    result = await list_teaching_courses(make_client())
    for course in result:
        assert set(course) == {"id", "name"}


async def test_list_teaching_courses_requests_teacher_enrollments(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=TEACHING_COURSES_URL,
        json=load_fixture("teacher_courses.json"),
    )
    from canvas_mcp.tools.teacher_assignments import list_teaching_courses
    await list_teaching_courses(make_client())
    request = httpx_mock.get_request()
    assert request.url.params["enrollment_type"] == "teacher"
    assert request.url.params["enrollment_state"] == "active"


async def test_list_teaching_courses_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=TEACHING_COURSES_URL,
        status_code=401,
    )
    from canvas_mcp.tools.teacher_assignments import list_teaching_courses
    result = await list_teaching_courses(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 401
