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


async def test_grade_report_returns_float_score(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(re.escape(f"{BASE_URL}/api/v1/courses")),
        json=load_fixture("courses_with_grades.json"),
    )
    from canvas_mcp.tools.grades import get_grade_report
    result = await get_grade_report(make_client())
    assert isinstance(result, list)
    ai_course = next(r for r in result if r["course_name"] == "ACS 4220 AI Engineering")
    assert ai_course["current_score"] == 88.5


async def test_grade_report_null_score_not_crash(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(re.escape(f"{BASE_URL}/api/v1/courses")),
        json=load_fixture("courses_with_grades.json"),
    )
    from canvas_mcp.tools.grades import get_grade_report
    result = await get_grade_report(make_client())
    web_course = next(r for r in result if r["course_name"] == "ACS 3930 Web APIs")
    assert web_course["current_score"] is None


async def test_grade_report_missing_enrollments_key(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(re.escape(f"{BASE_URL}/api/v1/courses")),
        json=load_fixture("courses_with_grades.json"),
    )
    from canvas_mcp.tools.grades import get_grade_report
    result = await get_grade_report(make_client())
    ds_course = next(r for r in result if r["course_name"] == "ACS 2000 Data Structures")
    assert ds_course["current_score"] is None


async def test_grade_report_result_shape(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(re.escape(f"{BASE_URL}/api/v1/courses")),
        json=load_fixture("courses_with_grades.json"),
    )
    from canvas_mcp.tools.grades import get_grade_report
    result = await get_grade_report(make_client())
    for item in result:
        assert "course_name" in item
        assert "current_score" in item


async def test_grade_report_requests_student_enrollments(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(re.escape(f"{BASE_URL}/api/v1/courses")),
        json=load_fixture("courses_with_grades.json"),
    )
    from canvas_mcp.tools.grades import get_grade_report
    await get_grade_report(make_client())
    request = httpx_mock.get_request()
    assert request.url.params["enrollment_type"] == "student"
    assert request.url.params["enrollment_state"] == "active"
    assert request.url.params["include[]"] == "total_scores"


async def test_grade_report_uses_student_enrollment_not_first(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(re.escape(f"{BASE_URL}/api/v1/courses")),
        json=[{
            "id": 104,
            "name": "ACS 4310 Systems",
            "enrollments": [
                {"type": "ta", "enrollment_state": "active"},
                {"type": "student", "enrollment_state": "active", "computed_current_score": 92.0},
            ],
        }],
    )
    from canvas_mcp.tools.grades import get_grade_report
    result = await get_grade_report(make_client())
    assert result == [{"course_name": "ACS 4310 Systems", "current_score": 92.0}]


async def test_grade_report_no_student_enrollment_returns_null(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(re.escape(f"{BASE_URL}/api/v1/courses")),
        json=[{
            "id": 105,
            "name": "ACS 4320 Security",
            "enrollments": [{"type": "observer", "enrollment_state": "active"}],
        }],
    )
    from canvas_mcp.tools.grades import get_grade_report
    result = await get_grade_report(make_client())
    assert result[0]["current_score"] is None


async def test_grade_report_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(re.escape(f"{BASE_URL}/api/v1/courses")),
        status_code=401,
    )
    from canvas_mcp.tools.grades import get_grade_report
    result = await get_grade_report(make_client())
    assert isinstance(result, dict)
    assert result["error"] == 401
