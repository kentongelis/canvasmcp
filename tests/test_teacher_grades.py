import json
from pathlib import Path
from pytest_httpx import HTTPXMock
from canvas_mcp.canvas_client import CanvasClient

BASE_URL = "https://canvas.example.com"
TOKEN = "test-token-abc"
FIXTURES = Path(__file__).parent / "fixtures"

COURSE_201_ENROLLMENTS_URL = (
    f"{BASE_URL}/api/v1/courses/201/enrollments"
    "?per_page=100&type[]=StudentEnrollment&include[]=current_points"
)


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def make_client() -> CanvasClient:
    return CanvasClient(base_url=BASE_URL, token=TOKEN)


def mock_enrollments(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=COURSE_201_ENROLLMENTS_URL, json=load_fixture("teacher_enrollments.json"))


async def test_class_grades_returns_float_score(httpx_mock: HTTPXMock):
    mock_enrollments(httpx_mock)
    from canvas_mcp.tools.teacher_grades import get_class_grades
    result = await get_class_grades(make_client(), 201)
    assert isinstance(result, list)
    by_name = {r["student_name"]: r for r in result}
    assert by_name["Ana Reyes"]["current_score"] == 91.25
    # Canvas can send a whole-number score as an int; it still comes back a float
    assert by_name["Dev Patel"]["current_score"] == 85.0
    assert isinstance(by_name["Dev Patel"]["current_score"], float)


async def test_class_grades_null_score_not_crash(httpx_mock: HTTPXMock):
    mock_enrollments(httpx_mock)
    from canvas_mcp.tools.teacher_grades import get_class_grades
    result = await get_class_grades(make_client(), 201)
    ben = next(r for r in result if r["student_name"] == "Ben Carter")
    assert ben["current_score"] is None


async def test_class_grades_missing_grades_key(httpx_mock: HTTPXMock):
    mock_enrollments(httpx_mock)
    from canvas_mcp.tools.teacher_grades import get_class_grades
    result = await get_class_grades(make_client(), 201)
    chloe = next(r for r in result if r["student_name"] == "Chloe Diaz")
    assert chloe["current_score"] is None


async def test_class_grades_result_shape_and_order(httpx_mock: HTTPXMock):
    mock_enrollments(httpx_mock)
    from canvas_mcp.tools.teacher_grades import get_class_grades
    result = await get_class_grades(make_client(), 201)
    for row in result:
        assert set(row) == {"student_name", "student_id", "current_score"}
    # One row per student (Dev's second-section enrollment is collapsed), sorted by name
    assert [(r["student_name"], r["student_id"]) for r in result] == [
        ("Ana Reyes", 501),
        ("Ben Carter", 502),
        ("Chloe Diaz", 503),
        ("Dev Patel", 504),
    ]


async def test_class_grades_requests_student_enrollments(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=COURSE_201_ENROLLMENTS_URL, json=[])
    from canvas_mcp.tools.teacher_grades import get_class_grades
    result = await get_class_grades(make_client(), 201)
    assert result == []
    request = httpx_mock.get_request()
    assert request.url.params["type[]"] == "StudentEnrollment"
    assert request.url.params["include[]"] == "current_points"


async def test_class_grades_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=COURSE_201_ENROLLMENTS_URL, status_code=401)
    from canvas_mcp.tools.teacher_grades import get_class_grades
    result = await get_class_grades(make_client(), 201)
    assert isinstance(result, dict)
    assert result["error"] == 401
