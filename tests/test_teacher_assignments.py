import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from pytest_httpx import HTTPXMock
from canvas_mcp.canvas_client import CanvasClient

BASE_URL = "https://canvas.example.com"
TOKEN = "test-token-abc"

FIXTURES = Path(__file__).parent / "fixtures"

TEACHING_COURSES_URL = (
    f"{BASE_URL}/api/v1/courses?enrollment_type=teacher&enrollment_state=active&per_page=100"
)

COURSE_201_ASSIGNMENTS_URL = f"{BASE_URL}/api/v1/courses/201/assignments?per_page=100"
COURSE_202_ASSIGNMENTS_URL = f"{BASE_URL}/api/v1/courses/202/assignments?per_page=100"

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


def mock_teaching_courses_and_assignments(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=TEACHING_COURSES_URL, json=load_fixture("teacher_courses.json"))
    httpx_mock.add_response(url=COURSE_201_ASSIGNMENTS_URL, json=load_fixture("teacher_assignments_course_201.json"))
    httpx_mock.add_response(url=COURSE_202_ASSIGNMENTS_URL, json=load_fixture("teacher_assignments_course_202.json"))


# ---------------------------------------------------------------------------
# get_teaching_deadlines
# ---------------------------------------------------------------------------

async def test_teaching_deadlines_sorted_across_two_courses(httpx_mock: HTTPXMock):
    mock_teaching_courses_and_assignments(httpx_mock)
    from canvas_mcp.tools.teacher_assignments import get_teaching_deadlines
    result = await get_teaching_deadlines(make_client(), days=7)

    assert isinstance(result, list)
    # With today = 2026-05-05 and days=7, window is May 5–May 12 UTC
    # Expected in order: REST Lab (May 6), Project Proposal (May 7), Midterm Exam (May 10)
    names = [r["name"] for r in result]
    assert names == ["REST Lab", "Project Proposal", "Midterm Exam"]


async def test_teaching_deadlines_excludes_past_due_far_future_and_undated(httpx_mock: HTTPXMock):
    mock_teaching_courses_and_assignments(httpx_mock)
    from canvas_mcp.tools.teacher_assignments import get_teaching_deadlines
    result = await get_teaching_deadlines(make_client(), days=7)
    names = [r["name"] for r in result]
    assert "Week 3 Reflection" not in names  # past due
    assert "Homework 2" not in names  # past due
    assert "Final Project" not in names  # outside the window
    assert "Participation" not in names  # no due date


async def test_teaching_deadlines_include_needs_grading_count(httpx_mock: HTTPXMock):
    mock_teaching_courses_and_assignments(httpx_mock)
    from canvas_mcp.tools.teacher_assignments import get_teaching_deadlines
    result = await get_teaching_deadlines(make_client(), days=7)
    for item in result:
        assert set(item) == {"name", "due_at", "course_name", "points_possible", "needs_grading_count"}
    by_name = {r["name"]: r for r in result}
    assert by_name["REST Lab"]["needs_grading_count"] == 5
    assert by_name["Midterm Exam"]["needs_grading_count"] == 0


async def test_teaching_deadlines_one_course_429_still_returns_other(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=TEACHING_COURSES_URL, json=load_fixture("teacher_courses.json"))
    httpx_mock.add_response(url=COURSE_201_ASSIGNMENTS_URL, status_code=429)
    httpx_mock.add_response(url=COURSE_202_ASSIGNMENTS_URL, json=load_fixture("teacher_assignments_course_202.json"))
    from canvas_mcp.tools.teacher_assignments import get_teaching_deadlines
    result = await get_teaching_deadlines(make_client(), days=7)
    assert isinstance(result, list)
    names = [r["name"] for r in result]
    assert names == ["REST Lab", "Midterm Exam"]


async def test_teaching_deadlines_courses_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=TEACHING_COURSES_URL, status_code=401)
    from canvas_mcp.tools.teacher_assignments import get_teaching_deadlines
    result = await get_teaching_deadlines(make_client(), days=7)
    assert isinstance(result, dict)
    assert result["error"] == 401


# ---------------------------------------------------------------------------
# get_grading_queue
# ---------------------------------------------------------------------------

async def test_grading_queue_only_needs_grading_sorted_most_first(httpx_mock: HTTPXMock):
    mock_teaching_courses_and_assignments(httpx_mock)
    from canvas_mcp.tools.teacher_assignments import get_grading_queue
    result = await get_grading_queue(make_client())

    assert isinstance(result, list)
    # Assignments with needs_grading_count == 0 are left out; the rest are sorted
    # across both courses, most ungraded first, regardless of due date
    assert [(r["name"], r["needs_grading_count"]) for r in result] == [
        ("Week 3 Reflection", 12),
        ("Homework 2", 8),
        ("REST Lab", 5),
        ("Participation", 3),
    ]


async def test_grading_queue_result_shape(httpx_mock: HTTPXMock):
    mock_teaching_courses_and_assignments(httpx_mock)
    from canvas_mcp.tools.teacher_assignments import get_grading_queue
    result = await get_grading_queue(make_client())
    for item in result:
        assert set(item) == {"name", "assignment_id", "course_id", "course_name", "due_at", "needs_grading_count"}
    top = result[0]
    assert top["assignment_id"] == 3002
    assert top["course_id"] == 201
    assert top["course_name"] == "ACS 4220 AI Engineering (Section 1)"


async def test_grading_queue_one_course_429_still_returns_other(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=TEACHING_COURSES_URL, json=load_fixture("teacher_courses.json"))
    httpx_mock.add_response(url=COURSE_201_ASSIGNMENTS_URL, status_code=429)
    httpx_mock.add_response(url=COURSE_202_ASSIGNMENTS_URL, json=load_fixture("teacher_assignments_course_202.json"))
    from canvas_mcp.tools.teacher_assignments import get_grading_queue
    result = await get_grading_queue(make_client())
    assert isinstance(result, list)
    assert [r["name"] for r in result] == ["Homework 2", "REST Lab"]


async def test_grading_queue_courses_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=TEACHING_COURSES_URL, status_code=401)
    from canvas_mcp.tools.teacher_assignments import get_grading_queue
    result = await get_grading_queue(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 401
