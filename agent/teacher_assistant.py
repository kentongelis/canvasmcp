import json
import os
import sys
import asyncio
import anthropic
from dotenv import load_dotenv

load_dotenv()

from canvas_mcp.canvas_client import CanvasClient
from canvas_mcp.tools.teacher_assignments import (
    list_teaching_courses,
    get_teaching_deadlines,
    get_grading_queue,
    get_missing_by_student,
    get_assignment_overview,
)
from canvas_mcp.tools.teacher_grades import get_class_grades
from canvas_mcp.tools.teacher_announcements import get_teaching_announcements

_api_key = os.getenv("ANTHROPIC_API_KEY")
if not _api_key:
    raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

anthropic_client = anthropic.AsyncAnthropic(api_key=_api_key)

TEACHER_SYSTEM_PROMPT = """You are a Canvas LMS teaching assistant. You help instructors see
what needs grading, upcoming deadlines in the courses they teach, how their class is doing,
which students are missing work, and their course announcements.

Rules:
- You are read-only. You cannot grade, post, message students, or change anything in
  Canvas. If asked to, say so and point the instructor to Canvas.
- When the user mentions a course or section by name (e.g. "my 4220 section", "my web
  class"), always call list_teaching_courses first to resolve the exact course ID before
  calling any course-specific tool (get_missing_by_student, get_class_grades,
  get_assignment_overview).
- For broad queries across all taught courses, prefer get_grading_queue and
  get_teaching_deadlines over per-course calls.
- Only call get_assignment_overview when the user asks about one specific assignment. If
  you don't have its ID, find it in get_teaching_deadlines or get_grading_queue results.
- Always include the course name when listing assignments or students.
- If a student's current_score is null, say no grades have been posted yet; never treat
  it as zero.
- If a tool returns an error dict with an "error" key, explain it to the user clearly
  without showing the raw error code.
- Never guess course IDs, assignment IDs, or student IDs — always resolve them from tool
  results."""

TOOLS = [
    {
        "name": "list_teaching_courses",
        "description": "List all active Canvas courses the current user teaches. Call this first when the user references a course by name.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_teaching_deadlines",
        "description": "Return assignments due within the next N days across all taught courses, sorted by due date, with needs_grading_count.",
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
        "name": "get_grading_queue",
        "description": "Return assignments with ungraded submissions across all taught courses, most ungraded first.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_missing_by_student",
        "description": "Return missing (unsubmitted, past-due, not excused) assignments in one course, grouped by student.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "integer",
                    "description": "Canvas course ID.",
                }
            },
            "required": ["course_id"],
        },
    },
    {
        "name": "get_class_grades",
        "description": "Return each student's current score in one course. Score is null if no grades have been posted yet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "integer",
                    "description": "Canvas course ID.",
                }
            },
            "required": ["course_id"],
        },
    },
    {
        "name": "get_teaching_announcements",
        "description": "Return recent announcements in taught courses. Optionally filter by keyword.",
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
        "name": "get_assignment_overview",
        "description": "Return details, rubric, and graded/ungraded/not-submitted counts for a specific assignment.",
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
    if tool_name == "list_teaching_courses":
        result = await list_teaching_courses(client)
    elif tool_name == "get_teaching_deadlines":
        result = await get_teaching_deadlines(client, days=tool_input.get("days", 7))
    elif tool_name == "get_grading_queue":
        result = await get_grading_queue(client)
    elif tool_name == "get_missing_by_student":
        result = await get_missing_by_student(client, course_id=tool_input["course_id"])
    elif tool_name == "get_class_grades":
        result = await get_class_grades(client, course_id=tool_input["course_id"])
    elif tool_name == "get_teaching_announcements":
        result = await get_teaching_announcements(client, keyword=tool_input.get("keyword"))
    elif tool_name == "get_assignment_overview":
        result = await get_assignment_overview(
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
            system=TEACHER_SYSTEM_PROMPT,
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
    question = " ".join(sys.argv[1:]) or "What needs grading this week?"
    print(asyncio.run(run_query(question)))
