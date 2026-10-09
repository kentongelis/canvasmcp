# Canvas MCP

A Python MCP server and agentic assistant for Canvas LMS that lets students ask natural language questions about their courses — deadlines, grades, missing work, and announcements — and get answers grounded in live Canvas API data.

**Course:** ACS 4220 (AI Engineering), Dominican University  
**Student:** Kenton Gelis  
**Last Updated:** 2026-10-09  
**Current Phase:** All six student tools, the agent loop and 62 passing tests are in place after a robustness pass (live-Canvas course filtering, full pagination, broader error handling); teacher tools are in progress and the live-Canvas check is still pending.

---

## What It Does

Students waste time manually clicking through Canvas across multiple courses to piece together what's due, what they're missing, and how they're doing. This project replaces that with a conversational interface:

> "What do I need to do this week?"  
> "Am I missing anything?"  
> "How are my grades looking?"  
> "What did my AI Engineering professor announce?"

The assistant calls live Canvas API endpoints, filters and sorts the results, and synthesizes a plain-language answer. It never hallucinates deadlines — every response is grounded in real data.

---

## How It Works

The project is built on two patterns that work together:

### 1. MCP Server (Model Context Protocol)

`canvas_mcp/server.py` exposes Canvas data as typed tools via the [MCP protocol](https://modelcontextprotocol.io). Each tool is a Python async function that calls the Canvas REST API and returns structured data. Wrapping Canvas in MCP means the data layer is reusable — Claude Desktop, a CLI, or any MCP-compatible client can connect to the same server without changing a line of tool code.

The six tools cover the core student workflow:

| Tool | What it does | Canvas endpoint | Status |
|---|---|---|---|
| `list_courses` | Active courses with IDs | `GET /courses?enrollment_state=active` | ✅ Complete |
| `get_upcoming_deadlines` | Assignments due within N days, sorted, cross-course | `GET /courses/:id/assignments` | ✅ Complete |
| `get_missing_assignments` | Past-due unsubmitted work (excused items filtered out) | `GET /users/self/missing_submissions` | ✅ Complete |
| `get_grade_report` | Current score per course from your student enrollment; `null` when no grades posted yet | `GET /courses?include[]=total_scores&enrollment_type=student` | ✅ Complete |
| `get_announcements` | Recent instructor posts, keyword-filterable | `GET /announcements` | ✅ Complete |
| `get_assignment_detail` | Full instructions and rubric for one assignment | `GET /courses/:id/assignments/:id` | ✅ Complete |

All list endpoints are fetched with `per_page=100` and follow Canvas's `Link` header, so courses with many assignments or students with many courses aren't cut off at Canvas's default page size of 10.

### 2. Agent SDK Loop

`agent/assistant.py` is a multi-step reasoning loop built with the Anthropic Python SDK. It handles queries that require more than one tool call — for example, "what should I study this weekend?" triggers the agent to fetch grades (to find weak courses), then fetch upcoming deadlines for those courses, then synthesize a prioritized plan.

The agent also resolves ambiguous references: if you say "my AI class," it calls `list_courses` first to find the matching course ID before fetching anything else. It never guesses IDs.

---

## Project Structure

```
canvasmcp/
├── canvas_mcp/
│   ├── server.py          # FastMCP server — registers all 6 tools
│   ├── canvas_client.py   # httpx wrapper with auth, error handling, pagination
│   └── tools/
│       ├── assignments.py  # list_courses, get_upcoming_deadlines, get_missing_assignments, get_assignment_detail
│       ├── grades.py       # get_grade_report
│       ├── announcements.py # get_announcements
│       └── teacher_assignments.py # list_teaching_courses (teacher tools, in progress)
├── agent/
│   └── assistant.py       # Anthropic SDK tool-use loop, system prompt, CLI entry
├── tests/
│   ├── test_canvas_client.py
│   ├── test_assignments.py
│   ├── test_grades.py
│   ├── test_announcements.py
│   ├── test_agent.py
│   ├── test_server.py
│   ├── test_teacher_assignments.py
│   └── fixtures/          # Mocked Canvas API JSON responses (no live Canvas needed)
├── .env.example
├── requirements.txt
├── pyproject.toml
├── CLAUDE.md
└── architecture.md
```

---

## Setup

### Prerequisites

- Python 3.11+
- A Canvas personal access token ([how to generate one](https://community.canvaslms.com/t5/Admin-Guide/How-do-I-manage-API-access-tokens-as-an-admin/ta-p/89))
- An Anthropic API key (for the agent; not needed to run the MCP server alone)

### Install

```bash
# Clone and enter the project
git clone <repo-url>
cd canvasmcp

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in all three values:

```
CANVAS_BASE_URL=https://your-institution.instructure.com
CANVAS_API_TOKEN=your_token_here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**`CANVAS_BASE_URL`** — the root domain your school uses, e.g. `https://dominican.instructure.com`.

**`CANVAS_API_TOKEN`** — generated in Canvas under **Account → Settings → Approved Integrations → New Access Token**.

**`ANTHROPIC_API_KEY`** — your key from [console.anthropic.com](https://console.anthropic.com). Required for the agent; not needed to run the MCP server alone.

The agent reads all keys from `.env` automatically via `python-dotenv`. If `ANTHROPIC_API_KEY` is missing it will raise a clear error at startup rather than failing silently.

---

## Running

### MCP Server (for Claude Desktop)

```bash
python3 -m canvas_mcp.server
```

The server starts on stdio transport. To connect it to Claude Desktop, add it to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "canvas": {
      "command": "/path/to/canvasmcp/.venv/bin/python",
      "args": ["-m", "canvas_mcp.server"],
      "env": {
        "PYTHONPATH": "/path/to/canvasmcp",
        "CANVAS_BASE_URL": "https://your-institution.instructure.com",
        "CANVAS_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

Replace `/path/to/canvasmcp` with the absolute path to your clone (run `pwd` inside it). On Windows, use `.venv\Scripts\python.exe` for `command`.

- **`command` must be the virtual environment's Python.** Claude Desktop launches the server outside your shell, so a bare `python3` resolves to the system interpreter, which doesn't have `mcp` or `httpx` installed.
- **`PYTHONPATH` is required.** Claude Desktop doesn't start the server from the project directory, so without it `-m canvas_mcp.server` fails with `No module named canvas_mcp`.
- After editing the config, fully quit and reopen Claude Desktop. If the tools don't appear, check the server logs (on macOS: `~/Library/Logs/Claude/mcp-server-canvas.log`).

Once connected, you can ask Claude Desktop questions like "what assignments do I have due this week?" and it will call the Canvas tools automatically.

### Agent (CLI)

```bash
python3 -m agent.assistant "what do I need to do this week?"
python3 -m agent.assistant "am I missing anything?"
python3 -m agent.assistant "how are my grades?"
python3 -m agent.assistant "what's due in my AI Engineering course?"
```

Run with no argument to use the default prompt:

```bash
python3 -m agent.assistant
# → "What do I need to do this week?"
```

---

## Running Tests

The test suite uses mocked HTTP responses — no live Canvas instance or API token required.

```bash
python3 -m pytest
```

To see each test by name:

```bash
python3 -m pytest -v
```

62 tests across 7 test files covering happy-path and error-path for every tool, plus client-level tests for pagination, 403/5xx responses, network failures and missing config.

---

## Implementation Status

### Completed ✅
- `CanvasClient`: httpx wrapper with Bearer auth, Link-header pagination with `per_page=100`, and error dicts for every non-2xx status, network failures, non-JSON responses and missing config
- All 6 MCP tools implemented and registered in the FastMCP server
- Course filtering reads Canvas's real response shape (`enrollments[].enrollment_state`)
- `get_grade_report` takes the score from the student enrollment, so a course where you're also a TA still reports your grade
- Agent SDK loop with multi-step tool chaining and ambiguous course resolution
- Claude Desktop setup instructions fixed (virtual environment's Python plus `PYTHONPATH`)
- Full test suite (62 tests, all passing)

### In Progress 🔄
- **Teacher tools** (read-only counterparts of the student tools). `list_teaching_courses` is implemented in `canvas_mcp/tools/teacher_assignments.py` with 4 passing tests, but it isn't registered in the MCP server yet. The other six teacher tools and `agent/teacher_assistant.py` haven't been started.

### Acceptance Criteria

- [x] `get_upcoming_deadlines(days=7)` returns correctly sorted results across ≥2 active courses
- [x] `get_missing_assignments` returns only unsubmitted, past-due items (not excused)
- [x] `get_grade_report` returns current score as a float; handles courses with no grades yet (`null`, not crash)
- [x] Agent correctly resolves ambiguous course references (e.g., "my CS class") via `list_courses` before fetching
- [x] All tools handle Canvas API errors (401, 404, 429) gracefully with descriptive messages. This now also covers 403, 5xx, network errors and missing config
- [x] Test suite covers happy path + error path for each tool using mocked HTTP responses
- [ ] Server starts in <2 seconds; individual tool calls complete in <3 seconds. Startup is met (~0.3s to load the server and register its tools). Tool-call latency hasn't been measured against live Canvas since the demo server was removed

### Milestones

| Week | Deliverable | Status |
|---|---|---|
| 1 | MCP server with `list_courses`, `get_upcoming_deadlines`, `get_missing_assignments` | ✅ Complete |
| 2 | Add `get_grade_report`, `get_announcements`, `get_assignment_detail` + test suite | ✅ Complete |
| 3 | Agent SDK loop, system prompt, multi-step query handling | ✅ Complete |
| 4 | Polish, README, presentation prep | 🔄 In Progress |

### Next Steps

1. **Run a live Canvas smoke test.** Generate a fresh Canvas token (the current one returns 401), then run each of the six tools against your real account. This confirms the course-filtering fix and lets us time each call against the <3 second goal.
2. **Continue the teacher tools.** Next up are `get_teaching_deadlines` and `get_grading_queue`, then the remaining teacher tools, registering them in the server, and `agent/teacher_assistant.py`.
3. **Update `architecture.md`**: its acceptance-criteria list still describes error handling as only 401/404/429.
4. **Prepare the presentation.**

---

## Error Handling

Every tool returns a descriptive error dict on API failures — it never raises an exception or crashes:

```python
{"error": 401, "message": "Unauthorized — check your Canvas API token."}
{"error": 403, "message": "Forbidden — your institution or instructor has not given you access to this Canvas data."}
{"error": 404, "message": "Resource not found."}
{"error": 429, "message": "Canvas rate limit exceeded. Wait before retrying."}
{"error": 500, "message": "Canvas server error (500). Try again later."}
{"error": "connection", "message": "Could not reach Canvas (ConnectError). Check CANVAS_BASE_URL and your network connection."}
{"error": "invalid_response", "message": "Canvas returned a non-JSON response — check that CANVAS_BASE_URL points to your Canvas instance."}
{"error": "config", "message": "CANVAS_API_TOKEN is not set. Add it to your .env file."}
```

Canvas usually throttles with a **403** whose body says "Rate Limit Exceeded" rather than a 429. The client detects this and returns the rate-limit message, so the agent says "wait" instead of "you don't have access".

Note: `get_missing_assignments` may return a 404 on some Canvas instances because institutions can disable this endpoint at the admin level. The agent is prompted to explain this to the user when it occurs.

---

## Tech Stack

| Layer | Technology |
|---|---|
| MCP Server | Python 3.11+, `mcp[cli]` (FastMCP), `httpx` |
| Agent | `anthropic` Python SDK, async tool-use loop |
| Canvas API | REST, Bearer token auth, Link-header pagination |
| Config | `python-dotenv`, `.env` |
| Testing | `pytest`, `pytest-asyncio`, `pytest-httpx` (mocked transport) |
| Transport | stdio (Claude Desktop) or SSE (HTTP server mode) |

---

## Architecture

See [`architecture.md`](architecture.md) for the full system diagram, pattern justifications, and risk analysis.
