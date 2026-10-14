import asyncio

from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.tools.assignments import (
    _deadlines_for_courses,
    _has_active_enrollment,
    get_assignment_detail,
)


async def list_teaching_courses(client: CanvasClient) -> list[dict] | dict:
    params = {"enrollment_type": "teacher", "enrollment_state": "active"}
    result = await client.get_all_pages("/courses", params=params)
    if isinstance(result, dict) and "error" in result:
        return result
    return [
        {"id": c["id"], "name": c["name"]}
        for c in result
        if _has_active_enrollment(c)
    ]


async def get_teaching_deadlines(client: CanvasClient, days: int = 7) -> list[dict] | dict:
    courses = await list_teaching_courses(client)
    if isinstance(courses, dict) and "error" in courses:
        return courses
    return await _deadlines_for_courses(
        client, courses, days, extra_fields=("needs_grading_count",)
    )


async def get_grading_queue(client: CanvasClient) -> list[dict] | dict:
    courses = await list_teaching_courses(client)
    if isinstance(courses, dict) and "error" in courses:
        return courses

    async def fetch_ungraded(course: dict) -> list[dict]:
        data = await client.get_all_pages(f"/courses/{course['id']}/assignments")
        if isinstance(data, dict) and "error" in data:
            return []
        return [
            {
                "name": a["name"],
                "assignment_id": a["id"],
                "course_id": course["id"],
                "course_name": course["name"],
                "due_at": a.get("due_at"),
                "needs_grading_count": a["needs_grading_count"],
            }
            for a in data
            if (a.get("needs_grading_count") or 0) > 0
        ]

    results = await asyncio.gather(
        *[fetch_ungraded(c) for c in courses],
        return_exceptions=True,
    )

    queue = []
    for batch in results:
        if isinstance(batch, list):
            queue.extend(batch)

    queue.sort(key=lambda a: a["needs_grading_count"], reverse=True)
    return queue


async def get_missing_by_student(client: CanvasClient, course_id: int) -> list[dict] | dict:
    params = {
        "student_ids[]": "all",
        "include[]": ["assignment", "user"],
    }
    data = await client.get_all_pages(f"/courses/{course_id}/students/submissions", params=params)
    if isinstance(data, dict) and "error" in data:
        return data

    by_student: dict[int, dict] = {}
    for s in data:
        if not s.get("missing") or s.get("excused") or s.get("submitted_at") is not None:
            continue
        user = s.get("user") or {}
        assignment = s.get("assignment") or {}
        student_id = s.get("user_id", user.get("id"))
        entry = by_student.setdefault(
            student_id,
            {"student_id": student_id, "student_name": user.get("name"), "missing": []},
        )
        entry["missing"].append(
            {
                "assignment_id": s.get("assignment_id", assignment.get("id")),
                "name": assignment.get("name"),
                "due_at": assignment.get("due_at"),
                "points_possible": assignment.get("points_possible"),
            }
        )

    students = list(by_student.values())
    for student in students:
        student["missing"].sort(key=lambda a: a["due_at"] or "")
    students.sort(key=lambda s: s["student_name"] or "")
    return students


async def get_assignment_overview(client: CanvasClient, course_id: int, assignment_id: int) -> dict:
    detail, summary = await asyncio.gather(
        get_assignment_detail(client, course_id, assignment_id),
        client.get(f"/courses/{course_id}/assignments/{assignment_id}/submission_summary"),
    )
    if isinstance(detail, dict) and "error" in detail:
        return detail
    if isinstance(summary, dict) and "error" in summary:
        return summary
    return {
        **detail,
        "submissions": {
            "graded": summary.get("graded", 0),
            "ungraded": summary.get("ungraded", 0),
            "not_submitted": summary.get("not_submitted", 0),
        },
    }
