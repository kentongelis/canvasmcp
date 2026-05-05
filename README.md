# Canvas MCP

A Python MCP server + agentic assistant for Canvas LMS.

**Course:** ACS 4220 (AI Engineering), Dominican University  
**Student:** Kenton Gelis  
**Last Updated:** 2026-05-05  
**Current Phase:** Architecture and planning complete; no source code implemented yet (Week 1 starting)

---

## Problem

Students waste time manually checking Canvas across courses to piece together deadlines, grades, and missing work. This project solves that with a conversational interface ("what do I need to do this week?") grounded in live Canvas API data.

---

## Implementation Status

### Completed
- Architecture design (`architecture.md`)
- Project planning and acceptance criteria (`CLAUDE.md`)

### In Progress
- Nothing yet

### Planned
- MCP server (`canvas_mcp/server.py`) with FastMCP
- Canvas API client (`canvas_mcp/canvas_client.py`) with httpx
- MCP tools: `list_courses`, `get_upcoming_deadlines`, `get_missing_assignments`
- MCP tools: `get_grade_report`, `get_announcements`, `get_assignment_detail`
- Agent SDK loop (`agent/assistant.py`)
- Test suite with mocked Canvas HTTP responses

---

## MCP Tools

| Tool | Canvas Endpoint | Status |
|---|---|---|
| `list_courses` | `GET /courses` | 🚧 Planned |
| `get_upcoming_deadlines` | `GET /courses/:id/assignments` | 🚧 Planned |
| `get_missing_assignments` | `GET /users/self/missing_submissions` | 🚧 Planned |
| `get_grade_report` | `GET /courses?include[]=total_scores` | 🚧 Planned |
| `get_announcements` | `GET /announcements` | 🚧 Planned |
| `get_assignment_detail` | `GET /courses/:id/assignments/:id` | 🚧 Planned |

---

## Acceptance Criteria

- [ ] `get_upcoming_deadlines(days=7)` returns correctly sorted results across ≥2 active courses
- [ ] `get_missing_assignments` returns only unsubmitted, past-due items (not excused)
- [ ] `get_grade_report` returns current score as a float; handles courses with no grades yet (returns `null`, not crash)
- [ ] Agent correctly resolves ambiguous course references (e.g., "my CS class") via `list_courses` before fetching
- [ ] All tools handle Canvas API errors (401, 404, 429) gracefully with descriptive messages
- [ ] Test suite covers happy path + error path for each tool using mocked HTTP responses
- [ ] Server starts in <2 seconds; individual tool calls complete in <3 seconds on a typical Canvas instance

---

## Project Structure

```
canvasmcp/
├── CLAUDE.md              # Project context and acceptance criteria
├── architecture.md        # System design, patterns, and architecture diagram
└── README.md
```

Target structure once implemented:

```
canvasmcp/
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

---

## Tech Stack

| Layer | Technology |
|---|---|
| MCP Server | Python 3.11+, `mcp` SDK, `httpx` |
| Agent | `anthropic` Python SDK, tool-use loop |
| Canvas API | REST, Bearer token auth |
| Config | `python-dotenv`, `.env` |
| Testing | `pytest`, `pytest-asyncio`, mocked responses |
| Transport | stdio (Claude Desktop) or SSE (HTTP server mode) |

---

## Setup

> No code to run yet. Setup instructions will be added once the MCP server is implemented.

Expected setup once available:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your Canvas token
python -m canvas_mcp.server
```

---

## Milestones

| Week | Deliverable | Status |
|---|---|---|
| 1 | MCP server with `list_courses`, `get_upcoming_deadlines`, `get_missing_assignments` | 🚧 Not started |
| 2 | Add `get_grade_report`, `get_announcements`, `get_assignment_detail` + test suite | 🚧 Not started |
| 3 | Agent SDK loop, system prompt, multi-step query handling | 🚧 Not started |
| 4 | Polish, CLAUDE.md, README, presentation prep | 🚧 Not started |

---

## Next Steps

1. Scaffold the Python package: `canvas_mcp/__init__.py`, `canvas_mcp/server.py`, `canvas_mcp/canvas_client.py`
2. Implement `list_courses` as the first tool (simplest; validates auth and client setup)
3. Add `get_upcoming_deadlines` with `days` parameter and sorting across courses
4. Add `get_missing_assignments` with excused-item filtering
5. Write happy-path + error-path tests for each Week 1 tool before moving to Week 2
6. Create `.env.example` and `requirements.txt`
