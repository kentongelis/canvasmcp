# Canvas MCP

A Python MCP server and agentic assistant for Canvas LMS that lets students ask natural language questions about their courses — deadlines, grades, missing work, and announcements — and get answers grounded in live Canvas API data.

**Course:** ACS 4220 (AI Engineering), Dominican University  
**Student:** Kenton Gelis  
**Last Updated:** 2026-05-05

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

| Tool | What it does | Canvas endpoint |
|---|---|---|
| `list_courses` | Active courses with IDs | `GET /courses` |
| `get_upcoming_deadlines` | Assignments due within N days, sorted, cross-course | `GET /courses/:id/assignments` |
| `get_missing_assignments` | Past-due unsubmitted work (excused items filtered out) | `GET /users/self/missing_submissions` |
| `get_grade_report` | Current score per course; `null` when no grades posted yet | `GET /courses?include[]=total_scores` |
| `get_announcements` | Recent instructor posts, keyword-filterable | `GET /announcements` |
| `get_assignment_detail` | Full instructions and rubric for one assignment | `GET /courses/:id/assignments/:id` |

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
│       └── announcements.py # get_announcements
├── agent/
│   └── assistant.py       # Anthropic SDK tool-use loop, system prompt, CLI entry
├── tests/
│   ├── test_canvas_client.py
│   ├── test_assignments.py
│   ├── test_grades.py
│   ├── test_announcements.py
│   ├── test_agent.py
│   ├── test_server.py
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

Edit `.env` and fill in both values:

```
CANVAS_BASE_URL=https://your-institution.instructure.com
CANVAS_API_TOKEN=your_token_here
```

Your Canvas base URL is the root domain your school uses — e.g. `https://dominican.instructure.com`. Your token is generated in Canvas under **Account → Settings → Approved Integrations → New Access Token**.

To use the agent you also need an Anthropic API key in your environment:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

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
      "command": "python3",
      "args": ["-m", "canvas_mcp.server"],
      "cwd": "/path/to/canvasmcp",
      "env": {
        "CANVAS_BASE_URL": "https://your-institution.instructure.com",
        "CANVAS_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

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

42 tests across 6 test files covering happy-path and error-path for every tool.

---

## Implementation Status

### Completed ✅
- `CanvasClient` — httpx wrapper with Bearer auth, 401/404/429 error handling, Link-header pagination
- All 6 MCP tools implemented and registered in the FastMCP server
- Agent SDK loop with multi-step tool chaining and ambiguous course resolution
- Full test suite (42 tests, all passing)

### Acceptance Criteria

- [x] `get_upcoming_deadlines(days=7)` returns correctly sorted results across ≥2 active courses
- [x] `get_missing_assignments` returns only unsubmitted, past-due items (not excused)
- [x] `get_grade_report` returns current score as a float; handles courses with no grades yet (`null`, not crash)
- [x] Agent correctly resolves ambiguous course references (e.g., "my CS class") via `list_courses` before fetching
- [x] All tools handle Canvas API errors (401, 404, 429) gracefully with descriptive messages
- [x] Test suite covers happy path + error path for each tool using mocked HTTP responses
- [x] Server starts in <2 seconds; individual tool calls complete in <3 seconds

### Milestones

| Week | Deliverable | Status |
|---|---|---|
| 1 | MCP server with `list_courses`, `get_upcoming_deadlines`, `get_missing_assignments` | ✅ Complete |
| 2 | Add `get_grade_report`, `get_announcements`, `get_assignment_detail` + test suite | ✅ Complete |
| 3 | Agent SDK loop, system prompt, multi-step query handling | ✅ Complete |
| 4 | Polish, README, presentation prep | 🔄 In Progress |

---

## Error Handling

Every tool returns a descriptive error dict on API failures — it never raises an exception or crashes:

```python
{"error": 401, "message": "Unauthorized — check your Canvas API token."}
{"error": 404, "message": "Resource not found."}
{"error": 429, "message": "Canvas rate limit exceeded. Wait before retrying."}
```

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
