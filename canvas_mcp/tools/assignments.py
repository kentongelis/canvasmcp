from canvas_mcp.canvas_client import CanvasClient


async def list_courses(client: CanvasClient) -> list[dict] | dict:
    result = await client.get_all_pages("/courses")
    if isinstance(result, dict) and "error" in result:
        return result
    return [
        {"id": c["id"], "name": c["name"]}
        for c in result
        if c.get("enrollment_state") == "active"
    ]
