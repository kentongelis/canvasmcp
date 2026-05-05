---
description: Update README.md to reflect current project state
---

Analyze the current state of the canvas-mcp project and update the existing README.md (or create one if it doesn't exist) to accurately reflect what has been implemented.

## Your task

**1. Scan the codebase to determine current state:**

- Check `canvas_mcp/tools/` for implemented MCP tools (assignments.py, grades.py, announcements.py)
- Check `canvas_mcp/server.py` for registered tools and server setup
- Check `canvas_mcp/canvas_client.py` for Canvas API integration completeness
- Check `agent/assistant.py` for Agent SDK loop implementation
- Check `tests/` for test coverage (which tools have tests, which have fixture data)
- Read `requirements.txt` or `pyproject.toml` for dependencies
- Read the existing `README.md` if it exists

**2. Update these sections based on what you found:**

- **Implementation Status:** Move items between Completed / In Progress / Planned based on actual code
- **MCP Tools table:** Update status (🚧 Planned → 🔄 In Progress → ✅ Complete) for each of the six tools: `list_courses`, `get_upcoming_deadlines`, `get_missing_assignments`, `get_grade_report`, `get_announcements`, `get_assignment_detail`
- **Acceptance Criteria checklist:** Check off items that are provably met by the current code
- **Project Structure:** Reflect actual files/folders that exist (omit files that don't exist yet)
- **Next Steps:** Remove completed items, add new tasks discovered during scan
- **Last Updated:** Change to today's date
- **Current Phase:** 1-sentence summary of where the project stands now (e.g., "Week 1 MCP tools complete, working on test suite")

**3. Provide a summary of what changed:**

- What moved from Planned → In Progress or Completed
- What new files or features were discovered
- What acceptance criteria are now met
- What still needs to be done before the next milestone

## Rules

- Only mark a tool "Completed" if it's fully implemented with a registered MCP tool, Canvas API call wired up, and tests passing
- Mark as "In Progress" if the file exists but isn't fully integrated or tested
- Be accurate — the README should match what's actually in the repo
- Use the Edit tool to make targeted updates to specific sections rather than rewriting the whole file
- Keep the existing README structure and tone
- Do not mark acceptance criteria as met unless you can point to specific code that satisfies each condition
