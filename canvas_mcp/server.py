from mcp.server.fastmcp import FastMCP
from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.tools.assignments import list_courses

mcp = FastMCP("canvas-mcp")


def _client() -> CanvasClient:
    return CanvasClient()


@mcp.tool()
async def list_courses_tool() -> list[dict] | dict:
    """List all active Canvas courses for the current user."""
    return await list_courses(_client())


if __name__ == "__main__":
    mcp.run()
