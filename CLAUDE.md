# Canvas MCP — Project Context for Claude Code

**Course:** ACS 4220 (AI Engineering), Dominican University  
**Student:** Kenton Gelis  

---

## Project Overview

A Python MCP server + agentic assistant for Canvas LMS. Students waste time manually checking Canvas across courses to piece together deadlines, grades, and missing work. This project solves that with a conversational interface ("what do I need to do this week?") grounded in live Canvas API data.

**Two core patterns:**
1. **MCP (Model Context Protocol)** — Python server (`FastMCP`) exposes Canvas REST API as typed tools. Decouples data access from reasoning; reusable across Claude Desktop, CLI, or web UI.
2. **Agent SDK** — `anthropic` Python SDK tool-use loop handles multi-step queries (fetch grades + deadlines + synthesize a study plan). Agent decides which tools to call and in what order.
3. **RAG (v2/bonus)** — Vector store (Chroma or sqlite-vec) over course syllabi/rubrics. Deferred until MVP is complete.

**Tech stack:** Python 3.11+, `mcp` SDK, `httpx`, `anthropic` SDK, `pytest`/`pytest-asyncio`, `python-dotenv`, stdio transport (Claude Desktop) or SSE (HTTP server mode).

---

## Repo Structure

```
canvas-mcp/
├── canvas_mcp/
│   ├── __init__.py
│   ├── server.py          # MCP server entry point (FastMCP)
│   ├── canvas_client.py   # httpx wrapper for Canvas REST API
│   └── tools/
│       ├── assignments.py
│       ├── grades.py
│       └── announcements.py
├── agent/
│   └── assistant.py       # Agent SDK loop, system prompt, tool routing
├── tests/
│   ├── test_assignments.py
│   ├── test_grades.py
│   └── fixtures/          # Mocked Canvas API responses
├── .env.example
├── CLAUDE.md
├── architecture.md
└── README.md
```

New tools go in `canvas_mcp/tools/`, their tests in `tests/`, mocked HTTP fixtures in `tests/fixtures/`, agent logic in `agent/assistant.py`.

---

## MCP Tools and Canvas API Map

| Tool | Canvas Endpoint | Returns |
|---|---|---|
| `list_courses` | `GET /courses` | Course names + IDs |
| `get_upcoming_deadlines` | `GET /courses/:id/assignments` | Sorted deadline list, configurable lookahead |
| `get_missing_assignments` | `GET /users/self/missing_submissions` | Unsubmitted past-due items (not excused) |
| `get_grade_report` | `GET /courses?include[]=total_scores` | Current + final grades per course |
| `get_announcements` | `GET /announcements` | Recent instructor posts, keyword-filterable |
| `get_assignment_detail` | `GET /courses/:id/assignments/:id` | Full instructions + rubric criteria |

Auth: Canvas personal access token in `.env` (Bearer token). No OAuth flow required.

**Canvas instance variability risk:** Some institutions disable API endpoints at the admin level. `missing_submissions` is particularly inconsistent depending on instructor configuration. Every tool must wrap Canvas calls in graceful error handling — return descriptive strings on 401/404/429, never crash.

---

## Spec With Teeth (Acceptance Criteria)

These are the hard pass/fail bar — concrete and falsifiable, not aspirational:

- [ ] `get_upcoming_deadlines(days=7)` returns correctly sorted results across ≥2 active courses
- [ ] `get_missing_assignments` returns only unsubmitted, past-due items (not excused)
- [ ] `get_grade_report` returns current score as a float; handles courses with no grades yet (returns `null`, not crash)
- [ ] Agent correctly resolves ambiguous course references (e.g., "my CS class") via `list_courses` before fetching
- [ ] All tools handle Canvas API errors (401, 404, 429) gracefully with descriptive messages
- [ ] Test suite covers happy path + error path for each tool using mocked HTTP responses
- [ ] Server starts in <2 seconds; individual tool calls complete in <3 seconds on a typical Canvas instance

---

## Test-First Development

Every tool needs both a happy-path and error-path test before it is considered done. Tests use `pytest` + `pytest-asyncio` with mocked Canvas HTTP responses in `tests/fixtures/` — no live Canvas instance required.

**Do not mark a tool complete unless its acceptance criterion above is met and tested.**

---

## Milestones

| Week | Deliverable |
|---|---|
| 1 | MCP server with `list_courses`, `get_upcoming_deadlines`, `get_missing_assignments` |
| 2 | Add `get_grade_report`, `get_announcements`, `get_assignment_detail` + test suite |
| 3 | Agent SDK loop, system prompt, multi-step query handling |
| 4 | Polish, CLAUDE.md, README, presentation prep |

Scope work to the current milestone — don't jump to agent work until MCP tools + tests from weeks 1–2 are solid.
