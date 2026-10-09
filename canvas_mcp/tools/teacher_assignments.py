from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.tools.assignments import _has_active_enrollment


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
