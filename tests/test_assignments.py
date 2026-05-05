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


# ---------------------------------------------------------------------------
# get_upcoming_deadlines
# ---------------------------------------------------------------------------

async def test_deadlines_sorted_across_two_courses(httpx_mock: HTTPXMock):
    # Courses endpoint (called by list_courses inside get_upcoming_deadlines)
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses",
        json=load_fixture("courses.json"),
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/101/assignments",
        json=load_fixture("assignments_course_101.json"),
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/courses/102/assignments",
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
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses", json=load_fixture("courses.json"))
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/101/assignments", json=load_fixture("assignments_course_101.json"))
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/102/assignments", json=load_fixture("assignments_course_102.json"))
    from canvas_mcp.tools.assignments import get_upcoming_deadlines
    result = await get_upcoming_deadlines(make_client(), days=7)
    names = [r["name"] for r in result]
    assert "Past Due Assignment" not in names
    assert "Far Future Assignment" not in names
    assert "No Due Date Assignment" not in names


async def test_deadlines_result_shape(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses", json=load_fixture("courses.json"))
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/101/assignments", json=load_fixture("assignments_course_101.json"))
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/102/assignments", json=load_fixture("assignments_course_102.json"))
    from canvas_mcp.tools.assignments import get_upcoming_deadlines
    result = await get_upcoming_deadlines(make_client(), days=7)
    for item in result:
        assert "name" in item
        assert "due_at" in item
        assert "course_name" in item
        assert "points_possible" in item


async def test_deadlines_one_course_429_still_returns_other(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses", json=load_fixture("courses.json"))
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/101/assignments", status_code=429)
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses/102/assignments", json=load_fixture("assignments_course_102.json"))
    from canvas_mcp.tools.assignments import get_upcoming_deadlines
    result = await get_upcoming_deadlines(make_client(), days=7)
    # Course 102 results should still come through
    assert isinstance(result, list)
    names = [r["name"] for r in result]
    assert "API Design Project" in names


async def test_deadlines_courses_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{BASE_URL}/api/v1/courses", status_code=401)
    from canvas_mcp.tools.assignments import get_upcoming_deadlines
    result = await get_upcoming_deadlines(make_client(), days=7)
    assert isinstance(result, dict)
    assert result["error"] == 401


# ---------------------------------------------------------------------------
# get_missing_assignments
# ---------------------------------------------------------------------------

async def test_missing_excludes_excused_and_submitted(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions",
        json=load_fixture("missing_submissions.json"),
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "Truly Missing Assignment"


async def test_missing_excludes_excused(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions",
        json=load_fixture("missing_submissions.json"),
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    names = [r["name"] for r in result]
    assert "Excused Assignment" not in names
    assert "Late Submitted Assignment" not in names


async def test_missing_result_shape(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions",
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
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions",
        json=[],
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    assert result == []


async def test_missing_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions",
        status_code=401,
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 401


async def test_missing_404_descriptive(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/users/self/missing_submissions",
        status_code=404,
    )
    from canvas_mcp.tools.assignments import get_missing_assignments
    result = await get_missing_assignments(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 404
