import asyncio
import re
from datetime import datetime, timedelta, timezone

from canvas_mcp.canvas_client import CanvasClient


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


async def list_courses(client: CanvasClient) -> list[dict] | dict:
    result = await client.get_all_pages("/courses")
    if isinstance(result, dict) and "error" in result:
        return result
    return [
        {"id": c["id"], "name": c["name"]}
        for c in result
        if c.get("enrollment_state") == "active"
    ]


async def get_upcoming_deadlines(client: CanvasClient, days: int = 7) -> list[dict] | dict:
    courses = await list_courses(client)
    if isinstance(courses, dict) and "error" in courses:
        return courses
    return await _deadlines_for_courses(client, courses, days)


async def _deadlines_for_courses(
    client: CanvasClient,
    courses: list[dict],
    days: int,
    extra_fields: tuple[str, ...] = (),
) -> list[dict]:
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=days)

    async def fetch_assignments(course: dict) -> list[dict]:
        data = await client.get(f"/courses/{course['id']}/assignments")
        if isinstance(data, dict) and "error" in data:
            return []
        items = []
        for a in data:
            due_at = a.get("due_at")
            if not due_at:
                continue
            due_dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            if now < due_dt <= window_end:
                item = {
                    "name": a["name"],
                    "due_at": due_at,
                    "course_name": course["name"],
                    "points_possible": a.get("points_possible"),
                }
                for field in extra_fields:
                    item[field] = a.get(field)
                items.append(item)
        return items

    results = await asyncio.gather(
        *[fetch_assignments(c) for c in courses],
        return_exceptions=True,
    )

    all_assignments = []
    for batch in results:
        if isinstance(batch, list):
            all_assignments.extend(batch)

    all_assignments.sort(key=lambda a: a["due_at"])
    return all_assignments


async def get_assignment_detail(client: CanvasClient, course_id: int, assignment_id: int) -> dict:
    data = await client.get(f"/courses/{course_id}/assignments/{assignment_id}")
    if isinstance(data, dict) and "error" in data:
        return data
    return {
        "name": data.get("name"),
        "description": _strip_html(data.get("description", "")),
        "due_at": data.get("due_at"),
        "points_possible": data.get("points_possible"),
        "rubric_criteria": data.get("rubric", []),
    }


async def get_missing_assignments(client: CanvasClient) -> list[dict] | dict:
    data = await client.get("/users/self/missing_submissions")
    if isinstance(data, dict) and "error" in data:
        return data
    return [
        {
            "name": a["name"],
            "due_at": a.get("due_at"),
            "points_possible": a.get("points_possible"),
            "course_id": a.get("course_id"),
        }
        for a in data
        if not a.get("excused") and a.get("submitted_at") is None
    ]
