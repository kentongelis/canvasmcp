import asyncio

from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.tools.assignments import _deadlines_for_courses, _has_active_enrollment


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
