from canvas_mcp.canvas_client import CanvasClient


def _student_enrollment(course: dict) -> dict:
    # A user can hold several enrollments in one course (e.g. TA + student);
    # only the student enrollment carries computed scores
    for e in course.get("enrollments") or []:
        if e.get("type") == "student":
            return e
    return {}


async def get_grade_report(client: CanvasClient) -> list[dict] | dict:
    data = await client.get_all_pages("/courses", params={
        "include[]": "total_scores",
        "enrollment_state": "active",
        "enrollment_type": "student",
    })
    if isinstance(data, dict) and "error" in data:
        return data
    return [
        {
            "course_name": c["name"],
            "current_score": _student_enrollment(c).get("computed_current_score"),
        }
        for c in data
    ]
