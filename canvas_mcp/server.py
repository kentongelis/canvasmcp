from mcp.server.fastmcp import FastMCP
from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.tools.assignments import list_courses, get_upcoming_deadlines, get_missing_assignments

mcp = FastMCP("canvas-mcp")


def _client() -> CanvasClient:
    return CanvasClient()


@mcp.tool()
async def list_courses_tool() -> list[dict] | dict:
    """List all active Canvas courses for the current user."""
    return await list_courses(_client())


@mcp.tool()
async def get_upcoming_deadlines_tool(days: int = 7) -> list[dict] | dict:
    """Return assignments due within the next `days` days, sorted by due date."""
    return await get_upcoming_deadlines(_client(), days=days)


@mcp.tool()
async def get_missing_assignments_tool() -> list[dict] | dict:
    """Return unsubmitted, past-due assignments that are not excused."""
    return await get_missing_assignments(_client())


if __name__ == "__main__":
    mcp.run()
