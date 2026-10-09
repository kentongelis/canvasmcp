from canvas_mcp.canvas_client import CanvasClient


async def get_grade_report(client: CanvasClient) -> list[dict] | dict:
    data = await client.get_all_pages("/courses", params={
        "include[]": "total_scores",
        "enrollment_state": "active",
    })
    if isinstance(data, dict) and "error" in data:
        return data
    return [
        {
            "course_name": c["name"],
            "current_score": c.get("enrollments", [{}])[0].get("computed_current_score"),
        }
        for c in data
    ]
