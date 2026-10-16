import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def tool_use(call_id: str, name: str, tool_input: dict):
    # MagicMock(name=...) sets the mock's repr name, not a .name attribute,
    # so assign it after construction.
    block = MagicMock(type="tool_use", id=call_id, input=tool_input)
    block.name = name
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [block]
    return response


def final_answer(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


# ---------------------------------------------------------------------------
# Teacher agent resolves a course reference via list_teaching_courses first
# ---------------------------------------------------------------------------

async def test_teacher_agent_resolves_course_before_course_tool():
    """
    For "who's missing work in my 4220 section?", the agent calls
    list_teaching_courses first, then get_missing_by_student with the resolved
    course ID, and the courses result is sent back to the model.
    """
    from agent.teacher_assistant import run_query

    courses_result = load_fixture("teacher_courses.json")[:2]
    call_order = []

    async def fake_list(client):
        call_order.append("list_teaching_courses")
        return courses_result

    async def fake_missing(client, course_id):
        call_order.append("get_missing_by_student")
        return []

    missing_mock = AsyncMock(side_effect=fake_missing)

    with patch("agent.teacher_assistant.anthropic_client") as mock_client, \
         patch("agent.teacher_assistant.list_teaching_courses", new=AsyncMock(side_effect=fake_list)), \
         patch("agent.teacher_assistant.get_missing_by_student", new=missing_mock):

        mock_client.messages.create = AsyncMock(side_effect=[
            tool_use("call_1", "list_teaching_courses", {}),
            tool_use("call_2", "get_missing_by_student", {"course_id": 201}),
            final_answer("Nobody is missing work in ACS 4220."),
        ])

        result = await run_query("who's missing work in my 4220 section?")

    assert result == "Nobody is missing work in ACS 4220."
    assert call_order == ["list_teaching_courses", "get_missing_by_student"]
    assert missing_mock.await_args.kwargs["course_id"] == 201

    # The list_teaching_courses result was sent back to the model. run_query
    # reuses one messages list, so read it by position: [user, assistant, tool_result, ...]
    messages = mock_client.messages.create.await_args.kwargs["messages"]
    tool_result = messages[2]["content"][0]
    assert tool_result["tool_use_id"] == "call_1"
    assert json.loads(tool_result["content"]) == courses_result


# ---------------------------------------------------------------------------
# Multi-step query — grading queue then class roster grades chained
# ---------------------------------------------------------------------------

async def test_teacher_agent_multi_step_grading_queue_then_roster():
    """
    Agent can chain the grading queue and a per-course roster call in one session.
    """
    from agent.teacher_assistant import run_query

    queue_mock = AsyncMock(return_value=[])
    grades_mock = AsyncMock(return_value=[])

    with patch("agent.teacher_assistant.anthropic_client") as mock_client, \
         patch("agent.teacher_assistant.get_grading_queue", new=queue_mock), \
         patch("agent.teacher_assistant.get_class_grades", new=grades_mock):

        mock_client.messages.create = AsyncMock(side_effect=[
            tool_use("call_1", "get_grading_queue", {}),
            tool_use("call_2", "get_class_grades", {"course_id": 202}),
            final_answer("Nothing to grade, and no grades posted yet in ACS 3930."),
        ])

        result = await run_query("what needs grading, and how is my web class doing?")

    assert isinstance(result, str)
    assert len(result) > 0
    queue_mock.assert_awaited_once()
    assert grades_mock.await_args.kwargs["course_id"] == 202
    assert mock_client.messages.create.await_count == 3


# ---------------------------------------------------------------------------
# Unknown tool name returns an error dict instead of raising
# ---------------------------------------------------------------------------

async def test_teacher_dispatch_unknown_tool_returns_error():
    from agent.teacher_assistant import _dispatch

    result = json.loads(await _dispatch("grade_submission", {}, MagicMock()))

    assert result["error"] == "unknown_tool"
    assert "grade_submission" in result["message"]


async def test_teacher_agent_uses_teacher_prompt_and_tools():
    """The loop sends the teacher system prompt and only teacher tools."""
    from agent.teacher_assistant import run_query, TEACHER_SYSTEM_PROMPT

    with patch("agent.teacher_assistant.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=final_answer("Hi."))
        await run_query("hello")

    kwargs = mock_client.messages.create.await_args.kwargs
    assert kwargs["system"] == TEACHER_SYSTEM_PROMPT
    assert {t["name"] for t in kwargs["tools"]} == {
        "list_teaching_courses",
        "get_teaching_deadlines",
        "get_grading_queue",
        "get_missing_by_student",
        "get_class_grades",
        "get_teaching_announcements",
        "get_assignment_overview",
    }
