import time


def test_server_imports_quickly():
    start = time.monotonic()
    import canvas_mcp.server  # noqa: F401
    elapsed = time.monotonic() - start
    assert elapsed < 2.0, f"Server import took {elapsed:.2f}s — must be under 2s"


STUDENT_TOOLS = {
    "list_courses_tool",
    "get_upcoming_deadlines_tool",
    "get_missing_assignments_tool",
    "get_grade_report_tool",
    "get_announcements_tool",
    "get_assignment_detail_tool",
}

TEACHER_TOOLS = {
    "list_teaching_courses_tool",
    "get_teaching_deadlines_tool",
    "get_grading_queue_tool",
    "get_missing_by_student_tool",
    "get_class_grades_tool",
    "get_teaching_announcements_tool",
    "get_assignment_overview_tool",
}


async def test_teacher_tools_registered():
    from canvas_mcp.server import mcp
    names = {t.name for t in await mcp.list_tools()}
    assert TEACHER_TOOLS <= names


async def test_all_tools_registered():
    from canvas_mcp.server import mcp
    names = {t.name for t in await mcp.list_tools()}
    assert names == STUDENT_TOOLS | TEACHER_TOOLS


async def test_teacher_course_tools_require_course_id():
    from canvas_mcp.server import mcp
    tools = {t.name: t for t in await mcp.list_tools()}
    for name in ("get_missing_by_student_tool", "get_class_grades_tool"):
        assert tools[name].inputSchema["required"] == ["course_id"]
    assert set(tools["get_assignment_overview_tool"].inputSchema["required"]) == {
        "course_id", "assignment_id",
    }
