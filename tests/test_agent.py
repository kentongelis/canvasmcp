import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------
# AC#4 — Agent resolves ambiguous course reference via list_courses first
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="implementation pending in agent/assistant.py")
async def test_agent_calls_list_courses_for_ambiguous_query():
    """
    When a query names a course ambiguously (e.g. "my AI class"), the agent
    must call list_courses before any course-specific tool, then use the
    resolved course ID in the follow-up tool call.
    """
    from agent.assistant import run_query

    # First response: model decides to call list_courses
    first_response = MagicMock()
    first_response.stop_reason = "tool_use"
    first_response.content = [
        MagicMock(
            type="tool_use",
            id="call_1",
            name="list_courses",
            input={},
        )
    ]

    # Second response: model uses list_courses result to call get_upcoming_deadlines
    second_response = MagicMock()
    second_response.stop_reason = "tool_use"
    second_response.content = [
        MagicMock(
            type="tool_use",
            id="call_2",
            name="get_upcoming_deadlines",
            input={"days": 7},
        )
    ]

    # Third response: model produces final text answer
    final_text = MagicMock()
    final_text.type = "text"
    final_text.text = "Your AI Engineering course has 2 assignments due this week."
    third_response = MagicMock()
    third_response.stop_reason = "end_turn"
    third_response.content = [final_text]

    courses_result = load_fixture("courses.json")
    deadlines_result = load_fixture("assignments_course_101.json")

    with patch("agent.assistant.anthropic_client") as mock_client, \
         patch("agent.assistant.list_courses", new=AsyncMock(return_value=courses_result)), \
         patch("agent.assistant.get_upcoming_deadlines", new=AsyncMock(return_value=deadlines_result)):

        mock_client.messages.create = AsyncMock(
            side_effect=[first_response, second_response, third_response]
        )

        result = await run_query("what's due in my AI class?")

    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Multi-step query — grade report then deadlines chained
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="implementation pending in agent/assistant.py")
async def test_agent_multi_step_grade_then_deadlines():
    """
    Agent can chain multiple tool calls in a single session without error.
    """
    from agent.assistant import run_query

    # Step 1: call get_grade_report
    response_1 = MagicMock()
    response_1.stop_reason = "tool_use"
    response_1.content = [
        MagicMock(type="tool_use", id="call_1", name="get_grade_report", input={})
    ]

    # Step 2: call get_upcoming_deadlines
    response_2 = MagicMock()
    response_2.stop_reason = "tool_use"
    response_2.content = [
        MagicMock(type="tool_use", id="call_2", name="get_upcoming_deadlines", input={"days": 7})
    ]

    # Step 3: final answer
    final_text = MagicMock()
    final_text.type = "text"
    final_text.text = "Focus on ACS 4220 — you have 2 assignments due and your grade is 88.5."
    response_3 = MagicMock()
    response_3.stop_reason = "end_turn"
    response_3.content = [final_text]

    with patch("agent.assistant.anthropic_client") as mock_client, \
         patch("agent.assistant.get_grade_report", new=AsyncMock(return_value=[])), \
         patch("agent.assistant.get_upcoming_deadlines", new=AsyncMock(return_value=[])):

        mock_client.messages.create = AsyncMock(
            side_effect=[response_1, response_2, response_3]
        )

        result = await run_query("what should I study this weekend?")

    assert isinstance(result, str)
    assert len(result) > 0
