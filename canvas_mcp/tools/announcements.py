import re
from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.tools.assignments import list_courses


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


async def get_announcements(client: CanvasClient, keyword: str = None) -> list[dict] | dict:
    courses = await list_courses(client)
    if isinstance(courses, dict) and "error" in courses:
        return courses
    return await _announcements_for_courses(client, courses, keyword)


async def _announcements_for_courses(
    client: CanvasClient, courses: list[dict], keyword: str = None
) -> list[dict] | dict:
    context_codes = [f"course_{c['id']}" for c in courses]
    params = {f"context_codes[]": context_codes}

    data = await client.get_all_pages("/announcements", params=params)
    if isinstance(data, dict) and "error" in data:
        return data

    results = []
    for a in data:
        title = a.get("title", "")
        message = _strip_html(a.get("message", ""))
        if keyword:
            kw = keyword.lower()
            if kw not in title.lower() and kw not in message.lower():
                continue
        results.append({
            "title": title,
            "message": message,
            "posted_at": a.get("posted_at"),
        })

    return results
