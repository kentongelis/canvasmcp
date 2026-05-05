import json
import sys
import asyncio
import anthropic

from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.tools.assignments import (
    list_courses,
    get_upcoming_deadlines,
    get_missing_assignments,
    get_assignment_detail,
)
from canvas_mcp.tools.grades import get_grade_report
from canvas_mcp.tools.announcements import get_announcements

anthropic_client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a Canvas LMS academic assistant. You help students understand
their upcoming deadlines, missing assignments, grades, and course announcements.

Rules:
- When a user mentions a course by name (e.g. "my AI class", "my web course"), always
  call list_courses first to resolve the exact course ID before calling any
  course-specific tool.
- For broad queries across all courses, prefer get_upcoming_deadlines and get_grade_report
  over per-course calls.
- Only call get_assignment_detail when the user is asking about one specific assignment
  by name or ID — do not use it for broad deadline queries.
- If get_missing_assignments returns an error, explain that the endpoint may be disabled
  at the student's institution and suggest checking Canvas directly.
- Always present deadlines in plain language with the course name included.
- If a tool returns an error dict with an "error" key, explain it to the user clearly
  without showing the raw error code.
- Never guess course IDs or assignment IDs — always resolve them from tool results."""

TOOLS = [
    {
        "name": "list_courses",
        "description": "List all active Canvas courses for the current user. Call this first when the user references a course by name.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_upcoming_deadlines",
        "description": "Return assignments due within the next N days, sorted by due date, across all active courses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look ahead. Defaults to 7.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_missing_assignments",
        "description": "Return unsubmitted, past-due assignments that are not excused.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_grade_report",
        "description": "Return the current grade for each active course. Score is null if no grades have been posted yet.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_announcements",
        "description": "Return recent Canvas announcements across all courses. Optionally filter by keyword.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Optional keyword to filter announcements by title or body.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_assignment_detail",
        "description": "Return full details and rubric criteria for a specific assignment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "integer",
                    "description": "Canvas course ID.",
                },
                "assignment_id": {
                    "type": "integer",
                    "description": "Canvas assignment ID.",
                },
            },
            "required": ["course_id", "assignment_id"],
        },
    },
]


async def _dispatch(tool_name: str, tool_input: dict, client: CanvasClient) -> str:
    if tool_name == "list_courses":
        result = await list_courses(client)
    elif tool_name == "get_upcoming_deadlines":
        result = await get_upcoming_deadlines(client, days=tool_input.get("days", 7))
    elif tool_name == "get_missing_assignments":
        result = await get_missing_assignments(client)
    elif tool_name == "get_grade_report":
        result = await get_grade_report(client)
    elif tool_name == "get_announcements":
        result = await get_announcements(client, keyword=tool_input.get("keyword"))
    elif tool_name == "get_assignment_detail":
        result = await get_assignment_detail(
            client,
            course_id=tool_input["course_id"],
            assignment_id=tool_input["assignment_id"],
        )
    else:
        result = {"error": "unknown_tool", "message": f"No tool named '{tool_name}'."}
    return json.dumps(result)


async def run_query(question: str) -> str:
    client = CanvasClient()
    messages = [{"role": "user", "content": question}]

    while True:
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text_blocks = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_blocks)

        # Process tool calls and collect results
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result_content = await _dispatch(block.name, block.input, client)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_content,
                })

        # Append the assistant turn and tool results, then loop
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What do I need to do this week?"
    print(asyncio.run(run_query(question)))
