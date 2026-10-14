from mcp.server.fastmcp import FastMCP
from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.tools.assignments import (
    list_courses,
    get_upcoming_deadlines,
    get_missing_assignments,
    get_assignment_detail,
)
from canvas_mcp.tools.grades import get_grade_report
from canvas_mcp.tools.announcements import get_announcements
from canvas_mcp.tools.teacher_assignments import (
    list_teaching_courses,
    get_teaching_deadlines,
    get_grading_queue,
    get_missing_by_student,
    get_assignment_overview,
)
from canvas_mcp.tools.teacher_grades import get_class_grades
from canvas_mcp.tools.teacher_announcements import get_teaching_announcements

mcp = FastMCP("canvas-mcp")


def _client() -> CanvasClient:
    return CanvasClient()


@mcp.tool()
async def list_courses_tool() -> list[dict] | dict:
    """List all active Canvas courses for the current user."""
    return await list_courses(_client())


@mcp.tool()
async def get_upcoming_deadlines_tool(days: int = 7) -> list[dict] | dict:
    """Return assignments due within the next `days` days, sorted by due date."""
    return await get_upcoming_deadlines(_client(), days=days)


@mcp.tool()
async def get_missing_assignments_tool() -> list[dict] | dict:
    """Return unsubmitted, past-due assignments that are not excused."""
    return await get_missing_assignments(_client())


@mcp.tool()
async def get_grade_report_tool() -> list[dict] | dict:
    """Return current grade for each active course. Score is null if no grades posted yet."""
    return await get_grade_report(_client())


@mcp.tool()
async def get_announcements_tool(keyword: str = None) -> list[dict] | dict:
    """Return recent Canvas announcements. Optionally filter by keyword."""
    return await get_announcements(_client(), keyword=keyword)


@mcp.tool()
async def get_assignment_detail_tool(course_id: int, assignment_id: int) -> dict:
    """Return full details and rubric for a specific assignment."""
    return await get_assignment_detail(_client(), course_id=course_id, assignment_id=assignment_id)



# --- Teacher tools (read-only) ---

@mcp.tool()
async def list_teaching_courses_tool() -> list[dict] | dict:
    """List all active Canvas courses the current user teaches."""
    return await list_teaching_courses(_client())


@mcp.tool()
async def get_teaching_deadlines_tool(days: int = 7) -> list[dict] | dict:
    """Return assignments due within the next `days` days across taught courses, sorted by due date, with needs_grading_count."""
    return await get_teaching_deadlines(_client(), days=days)


@mcp.tool()
async def get_grading_queue_tool() -> list[dict] | dict:
    """Return assignments with ungraded submissions across taught courses, most ungraded first."""
    return await get_grading_queue(_client())


@mcp.tool()
async def get_missing_by_student_tool(course_id: int) -> list[dict] | dict:
    """Return missing (unsubmitted, not excused) assignments in a course, grouped by student."""
    return await get_missing_by_student(_client(), course_id=course_id)


@mcp.tool()
async def get_class_grades_tool(course_id: int) -> list[dict] | dict:
    """Return each student's current score in a course. Score is null if no grades posted yet."""
    return await get_class_grades(_client(), course_id=course_id)


@mcp.tool()
async def get_teaching_announcements_tool(keyword: str = None) -> list[dict] | dict:
    """Return recent announcements in taught courses. Optionally filter by keyword."""
    return await get_teaching_announcements(_client(), keyword=keyword)


@mcp.tool()
async def get_assignment_overview_tool(course_id: int, assignment_id: int) -> dict:
    """Return details, rubric, and graded/ungraded/not-submitted counts for an assignment."""
    return await get_assignment_overview(_client(), course_id=course_id, assignment_id=assignment_id)


if __name__ == "__main__":
    mcp.run()
