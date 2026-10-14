from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.tools.announcements import _announcements_for_courses
from canvas_mcp.tools.teacher_assignments import list_teaching_courses


async def get_teaching_announcements(client: CanvasClient, keyword: str = None) -> list[dict] | dict:
    courses = await list_teaching_courses(client)
    if isinstance(courses, dict) and "error" in courses:
        return courses
    return await _announcements_for_courses(client, courses, keyword)
