import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from pytest_httpx import HTTPXMock
from canvas_mcp.canvas_client import CanvasClient

BASE_URL = "https://canvas.example.com"
TOKEN = "test-token-abc"

FIXTURES = Path(__file__).parent / "fixtures"

COURSES_URL = f"{BASE_URL}/api/v1/courses?enrollment_state=active&per_page=100"

# Fixture due dates are written relative to this date
FROZEN_NOW = datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN_NOW if tz else FROZEN_NOW.replace(tzinfo=None)


@pytest.fixture(autouse=True)
def freeze_time(monkeypatch):
    monkeypatch.setattr("canvas_mcp.tools.assignments.datetime", _FrozenDatetime)


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def make_client() -> CanvasClient:
    return CanvasClient(base_url=BASE_URL, token=TOKEN)


# ---------------------------------------------------------------------------
# list_courses
# ---------------------------------------------------------------------------

async def test_list_courses_returns_only_active(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=COURSES_URL,
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
        url=COURSES_URL,
        json=load_fixture("courses.json"),
    )
    from canvas_mcp.tools.assignments import list_courses
    result = await list_courses(make_client())
    for course in result:
        assert "id" in course
        assert "name" in course


async def test_list_courses_requests_active_enrollments(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=COURSES_URL, json=load_fixture("courses.json"))
    from canvas_mcp.tools.assignments import list_courses
    await list_courses(make_client())
    request = httpx_mock.get_request()
    assert request.url.params["enrollment_state"] == "active"
    assert request.url.params["per_page"] == "100"


async def test_list_courses_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=COURSES_URL,
        status_code=401,
    )
    from canvas_mcp.tools.assignments import list_courses
    result = await list_courses(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 401


# ---------------------------------------------------------------------------
# get_upcoming_deadlines
# ---------------------------------------------------------------------------

async def test_deadlines_sorted_across_two_courses(httpx_mock: HTTPXMock):
    # Courses endpoint (called by list_courses inside get_upcoming_deadlines)
    httpx_mock.add_response(
        url=COURSES_URL,
        json=load_fixture("courses.json"),
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/101/assignments?per_page=100",
        json=load_fixture("assignments_course_101.json"),
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/102/assignments?per_page=100",
        json=load_fixture("assignments_course_102.json"),
    )
    from canvas_mcp.tools.assignments import get_upcoming_deadlines
    result = await get_upcoming_deadlines(make_client(), days=7)

    assert isinstance(result, list)
    # With today = 2026-05-05 and days=7, window is May 5–May 12 UTC
    # Expected in order: API Design Project (May 6), Midterm Essay (May 8), Lab Report (May 11)
    names = [r["name"] for r in result]
    assert names == ["API Design Project", "Midterm Essay", "Lab Report"]


async def test_deadlines_excludes_past_due(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=COURSES_URL, json=load_fixture("courses.json"))
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/101/assignments?per_page=100", json=load_fixture("assignments_course_101.json"))
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/102/assignments?per_page=100", json=load_fixture("assignments_course_102.json"))
    from canvas_mcp.tools.assignments import get_upcoming_deadlines
    result = await get_upcoming_deadlines(make_client(), days=7)
    names = [r["name"] for r in result]
    assert "Past Due Assignment" not in names
    assert "Far Future Assignment" not in names
    assert "No Due Date Assignment" not in names


async def test_deadlines_result_shape(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=COURSES_URL, json=load_fixture("courses.json"))
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/101/assignments?per_page=100", json=load_fixture("assignments_course_101.json"))
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/102/assignments?per_page=100", json=load_fixture("assignments_course_102.json"))
    from canvas_mcp.tools.assignments import get_upcoming_deadlines
    result = await get_upcoming_deadlines(make_client(), days=7)
    for item in result:
        assert "name" in item
        assert "due_at" in item
        assert "course_name" in item
        assert "points_possible" in item


async def test_deadlines_one_course_429_still_returns_other(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=COURSES_URL, json=load_fixture("courses.json"))
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/101/assignments?per_page=100", status_code=429)
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/102/assignments?per_page=100", json=load_fixture("assignments_course_102.json"))
    from canvas_mcp.tools.assignments import get_upcoming_deadlines
    result = await get_upcoming_deadlines(make_client(), days=7)
    # Course 102 results should still come through
    assert isinstance(result, list)
    names = [r["name"] for r in result]
    assert "API Design Project" in names


async def test_deadlines_follows_assignment_pagination(httpx_mock: HTTPXMock):
    page2_url = f"{BASE_URL}/api/v1/courses/101/assignments?page=2&per_page=100"
    page1 = [a for a in load_fixture("assignments_course_101.json") if a["name"] != "Midterm Essay"]
    page2 = [a for a in load_fixture("assignments_course_101.json") if a["name"] == "Midterm Essay"]
    httpx_mock.add_response(url=COURSES_URL, json=load_fixture("courses.json"))
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/101/assignments?per_page=100",
        json=page1,
        headers={"Link": f'<{page2_url}>; rel="next"'},
    )
    httpx_mock.add_response(url=page2_url, json=page2)
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/102/assignments?per_page=100", json=load_fixture("assignments_course_102.json"))
    from canvas_mcp.tools.assignments import get_upcoming_deadlines
    result = await get_upcoming_deadlines(make_client(), days=7)
    names = [r["name"] for r in result]
    assert names == ["API Design Project", "Midterm Essay", "Lab Report"]


async def test_deadlines_courses_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=COURSES_URL, status_code=401)
    from canvas_mcp.tools.assignments import get_upcoming_deadlines
    result = await get_upcoming_deadlines(make_client(), days=7)
    assert isinstance(result, dict)
    assert result["error"] == 401


# ---------------------------------------------------------------------------
# get_missing_assignments
# ---------------------------------------------------------------------------

async def test_missing_excludes_excused_and_submitted(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions?per_page=100",
        json=load_fixture("missing_submissions.json"),
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "Truly Missing Assignment"


async def test_missing_excludes_excused(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions?per_page=100",
        json=load_fixture("missing_submissions.json"),
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    names = [r["name"] for r in result]
    assert "Excused Assignment" not in names
    assert "Late Submitted Assignment" not in names


async def test_missing_result_shape(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions?per_page=100",
        json=load_fixture("missing_submissions.json"),
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    for item in result:
        assert "name" in item
        assert "due_at" in item
        assert "points_possible" in item


async def test_missing_empty_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions?per_page=100",
        json=[],
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    assert result == []


async def test_missing_follows_pagination(httpx_mock: HTTPXMock):
    page2_url = f"{BASE_URL}/api/v1/users/self/missing_submissions?page=2&per_page=100"
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions?per_page=100",
        json=[],
        headers={"Link": f'<{page2_url}>; rel="next"'},
    )
    httpx_mock.add_response(url=page2_url, json=load_fixture("missing_submissions.json"))
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    assert [r["name"] for r in result] == ["Truly Missing Assignment"]


async def test_missing_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions?per_page=100",
        status_code=401,
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 401


async def test_missing_404_descriptive(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions?per_page=100",
        status_code=404,
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 404


# ---------------------------------------------------------------------------
# get_assignment_detail
# ---------------------------------------------------------------------------

async def test_assignment_detail_happy_path(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/101/assignments/1001",
        json=load_fixture("assignment_detail.json"),
    )
    from canvas_mcp.tools.assignments import get_assignment_detail
    result = await get_assignment_detail(make_client(), course_id=101, assignment_id=1001)
    assert result["name"] == "Midterm Essay"
    assert result["points_possible"] == 100
    assert result["due_at"] == "2026-05-08T23:59:00Z"
    assert len(result["rubric_criteria"]) == 4


async def test_assignment_detail_html_stripped(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/101/assignments/1001",
        json=load_fixture("assignment_detail.json"),
    )
    from canvas_mcp.tools.assignments import get_assignment_detail
    result = await get_assignment_detail(make_client(), course_id=101, assignment_id=1001)
    assert "<" not in result["description"]
    assert ">" not in result["description"]
    assert "2000-word" in result["description"]


async def test_assignment_detail_no_rubric(httpx_mock: HTTPXMock):
    no_rubric = {**load_fixture("assignment_detail.json")}
    del no_rubric["rubric"]
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/101/assignments/1001",
        json=no_rubric,
    )
    from canvas_mcp.tools.assignments import get_assignment_detail
    result = await get_assignment_detail(make_client(), course_id=101, assignment_id=1001)
    assert result["rubric_criteria"] == []


async def test_assignment_detail_result_shape(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/101/assignments/1001",
        json=load_fixture("assignment_detail.json"),
    )
    from canvas_mcp.tools.assignments import get_assignment_detail
    result = await get_assignment_detail(make_client(), course_id=101, assignment_id=1001)
    for key in ("name", "description", "due_at", "points_possible", "rubric_criteria"):
        assert key in result


async def test_assignment_detail_404(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/101/assignments/9999",
        status_code=404,
    )
    from canvas_mcp.tools.assignments import get_assignment_detail
    result = await get_assignment_detail(make_client(), course_id=101, assignment_id=9999)
    assert isinstance(result, dict)
    assert result["error"] == 404


async def test_assignment_detail_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/101/assignments/1001",
        status_code=401,
    )
    from canvas_mcp.tools.assignments import get_assignment_detail
    result = await get_assignment_detail(make_client(), course_id=101, assignment_id=1001)
    assert isinstance(result, dict)
    assert result["error"] == 401
