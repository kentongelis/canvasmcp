# Canvas MCP

An [MCP](https://modelcontextprotocol.io) server that connects Claude (or any MCP client) to your [Canvas LMS](https://www.instructure.com/canvas) account. Ask about deadlines, grades, missing work and announcements in plain language, and get answers pulled from live Canvas data.

> "What do I need to do this week?"
> "Am I missing anything?"
> "How are my grades looking?"
> "What did my biology professor announce?"

It also includes a small command-line assistant built on the Anthropic API, for use outside an MCP client.

---

## Features

- **Six read-only Canvas tools.** Courses, upcoming deadlines, missing work, grades, announcements and assignment details.
- **Works with any Canvas instance.** You only need your school's Canvas URL and a personal access token. No OAuth app or admin setup.
- **Never writes to Canvas.** Every tool only reads data, so nothing can submit, edit or delete anything.
- **Handles real-world Canvas quirks.** It fetches every page of results, filters out inactive courses, and returns readable errors instead of crashing (bad token, disabled endpoint, rate limit, network failure).

---

## Tools

| Tool | What it returns | Canvas endpoint |
|---|---|---|
| `list_courses_tool` | Your active courses with their IDs | `GET /courses` |
| `get_upcoming_deadlines_tool(days=7)` | Assignments due in the next *N* days across all courses, soonest first | `GET /courses/:id/assignments` |
| `get_missing_assignments_tool` | Past-due work you haven't submitted (excused items are left out) | `GET /users/self/missing_submissions` |
| `get_grade_report_tool` | Current score per course, or `null` if nothing has been graded yet | `GET /courses?include[]=total_scores` |
| `get_announcements_tool(keyword=None)` | Recent announcements, optionally filtered by a keyword | `GET /announcements` |
| `get_assignment_detail_tool(course_id, assignment_id)` | Full instructions and rubric for one assignment | `GET /courses/:id/assignments/:id` |

---

## Quick start

### 1. Requirements

- Python 3.11 or newer
- A Canvas account at your school
- An Anthropic API key, only if you want to use the command-line assistant

### 2. Install

```bash
git clone https://github.com/kentongelis/canvasmcp.git
cd canvasmcp

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Get a Canvas access token

1. Log in to Canvas and open **Account → Settings**.
2. Under **Approved Integrations**, click **+ New Access Token**.
3. Give it a name (e.g. "Canvas MCP"), optionally an expiry date, and click **Generate Token**.
4. Copy the token now. Canvas won't show it again.

Your token has the same access as your Canvas account, so treat it like a password and don't commit it.

### 4. Configure

```bash
cp .env.example .env
```

Then edit `.env`:

```
CANVAS_BASE_URL=https://your-school.instructure.com
CANVAS_API_TOKEN=your_token_here
ANTHROPIC_API_KEY=sk-ant-...      # only needed for the CLI assistant
```

`CANVAS_BASE_URL` is the address you see in the browser when you're logged in to Canvas, without any path (e.g. `https://canvas.myschool.edu` or `https://myschool.instructure.com`).

---

## Using it with Claude Desktop

Open Claude Desktop's config file (**Settings → Developer → Edit Config**), or edit it directly:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add a `canvas` entry under `mcpServers`:

```json
{
  "mcpServers": {
    "canvas": {
      "command": "/absolute/path/to/canvasmcp/.venv/bin/python",
      "args": ["-m", "canvas_mcp.server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/canvasmcp",
        "CANVAS_BASE_URL": "https://your-school.instructure.com",
        "CANVAS_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

Replace `/absolute/path/to/canvasmcp` with the output of `pwd` from inside the project folder. On Windows, `command` is `C:\\path\\to\\canvasmcp\\.venv\\Scripts\\python.exe`.

Two details that commonly trip people up:

- **`command` must point at the virtual environment's Python.** Claude Desktop doesn't use your shell, so a plain `python3` finds the system Python, which doesn't have the dependencies installed.
- **`PYTHONPATH` is required.** Claude Desktop doesn't start the server from the project folder, so without it you'll get `No module named canvas_mcp`.

Fully quit and reopen Claude Desktop. The Canvas tools should appear under the tools menu in a new chat. Try "what's due this week?"

If they don't show up, check the server log. On macOS it's at `~/Library/Logs/Claude/mcp-server-canvas.log`.

## Using it with Claude Code

From inside the project folder:

```bash
claude mcp add canvas \
  -e PYTHONPATH="$(pwd)" \
  -e CANVAS_BASE_URL=https://your-school.instructure.com \
  -e CANVAS_API_TOKEN=your_token_here \
  -- "$(pwd)/.venv/bin/python" -m canvas_mcp.server
```

## Using it with other MCP clients

The server uses the standard stdio transport. Any MCP client can launch it with:

```bash
/path/to/canvasmcp/.venv/bin/python -m canvas_mcp.server
```

Set `CANVAS_BASE_URL` and `CANVAS_API_TOKEN` in the environment, or in a `.env` file in the folder the server runs from.

To try the tools interactively without a chat client, use the MCP Inspector that comes with `mcp[cli]`:

```bash
mcp dev canvas_mcp/server.py
```

---

## Command-line assistant

`agent/assistant.py` is a standalone assistant that uses Claude through the Anthropic API. It calls the same Canvas tools, chaining several of them when a question needs it. For example, to answer "what's due in my chemistry class?" it first looks up your courses to find which one is chemistry.

It needs `ANTHROPIC_API_KEY` in `.env`.

```bash
python -m agent.assistant "what do I need to do this week?"
python -m agent.assistant "am I missing anything?"
python -m agent.assistant "how are my grades?"
python -m agent.assistant          # defaults to "What do I need to do this week?"
```

---

## Errors and limitations

When Canvas returns an error, the tools return a short explanation instead of crashing, so Claude can tell you what went wrong:

| Situation | What you'll see |
|---|---|
| Invalid or expired token | `401 Unauthorized — check your Canvas API token.` |
| Your school or instructor has blocked the data | `403 Forbidden — ...` |
| Endpoint or item doesn't exist | `404 Resource not found.` |
| Too many requests | `Canvas rate limit exceeded. Wait before retrying.` (Canvas usually signals this with a 403, which is detected) |
| Canvas is down | `Canvas server error (5xx). Try again later.` |
| Wrong URL or no network | `Could not reach Canvas ... Check CANVAS_BASE_URL ...` |
| `.env` not filled in | `CANVAS_API_TOKEN is not set.` |

Known limitations:

- **Missing submissions may not work at your school.** Some Canvas administrators disable `/users/self/missing_submissions`. If so, that tool returns a 404 and the other tools are unaffected.
- **Grades reflect what Canvas shows you.** If an instructor hides grades or the final grade, the score will be `null` or out of date.
- **Read-only.** Nothing can submit assignments or post to Canvas, by design.

---

## Development

### Project layout

```
canvasmcp/
├── canvas_mcp/
│   ├── server.py            # FastMCP server; registers the tools
│   ├── canvas_client.py     # httpx client: auth, pagination, error handling
│   └── tools/
│       ├── assignments.py   # courses, deadlines, missing work, assignment detail
│       ├── grades.py        # grade report
│       ├── announcements.py # announcements
│       ├── teacher_assignments.py  # teacher tools (not yet registered)
│       └── teacher_grades.py       # teacher tools (not yet registered)
├── agent/
│   └── assistant.py         # Anthropic API tool-use loop and CLI
├── tests/                   # pytest suite
│   └── fixtures/            # mocked Canvas API responses
├── .env.example
├── requirements.txt
└── architecture.md          # design notes
```

### Running the tests

The tests mock all Canvas HTTP calls, so you don't need a Canvas account or token:

```bash
python -m pytest
```

### Adding a tool

1. Write an async function in `canvas_mcp/tools/` that takes a `CanvasClient` and returns data or the client's error dict.
2. Register it in `canvas_mcp/server.py` with `@mcp.tool()`.
3. To make it available to the CLI assistant, add it to `TOOLS` and the dispatcher in `agent/assistant.py`.
4. Add a fixture in `tests/fixtures/`, plus a test for the normal case and one for an error.

### Roadmap

- **Teacher tools.** Read-only tools for instructors: teaching courses, upcoming deadlines with ungraded counts, a grading queue, missing work by student and class grades. They're written and tested in `canvas_mcp/tools/teacher_*.py` but not yet exposed by the server.

See [`architecture.md`](architecture.md) for design details.
