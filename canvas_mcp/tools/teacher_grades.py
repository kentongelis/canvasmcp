from canvas_mcp.canvas_client import CanvasClient


def _as_float(score) -> float | None:
    return float(score) if score is not None else None


async def get_class_grades(client: CanvasClient, course_id: int) -> list[dict] | dict:
    data = await client.get_all_pages(f"/courses/{course_id}/enrollments", params={
        "type[]": "StudentEnrollment",
        "include[]": "current_points",
    })
    if isinstance(data, dict) and "error" in data:
        return data

    # A student enrolled in several sections of one course shows up once per
    # section with the same course-level grades; keep one row per student
    by_student: dict[int, dict] = {}
    for e in data:
        user = e.get("user") or {}
        student_id = e.get("user_id", user.get("id"))
        if student_id in by_student:
            continue
        by_student[student_id] = {
            "student_name": user.get("name"),
            "student_id": student_id,
            "current_score": _as_float((e.get("grades") or {}).get("current_score")),
        }

    return sorted(by_student.values(), key=lambda s: s["student_name"] or "")
