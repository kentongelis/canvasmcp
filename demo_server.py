"""
Fake Canvas API server for demo purposes.
Serves realistic canned responses so the agent works without a real Canvas token.

Usage:
    python3 demo_server.py
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

COURSES = [
    {"id": 101, "name": "ACS 4220 AI Engineering", "enrollment_state": "active"},
    {"id": 102, "name": "ACS 3930 Web APIs", "enrollment_state": "active"},
    {"id": 103, "name": "ACS 3210 Databases", "enrollment_state": "active"},
]

ASSIGNMENTS_101 = [
    {"id": 1001, "name": "Agent SDK Project", "due_at": "2026-05-09T23:59:00Z", "points_possible": 100},
    {"id": 1002, "name": "MCP Presentation", "due_at": "2026-05-12T23:59:00Z", "points_possible": 50},
]

ASSIGNMENTS_102 = [
    {"id": 2001, "name": "REST API Design Lab", "due_at": "2026-05-07T23:59:00Z", "points_possible": 80},
    {"id": 2002, "name": "OpenAPI Spec Write-up", "due_at": "2026-05-11T23:59:00Z", "points_possible": 40},
]

ASSIGNMENTS_103 = [
    {"id": 3001, "name": "Query Optimization Report", "due_at": "2026-05-08T23:59:00Z", "points_possible": 60},
]

MISSING = [
    {
        "id": 4001,
        "name": "Week 3 Reading Reflection",
        "due_at": "2026-04-28T23:59:00Z",
        "points_possible": 20,
        "excused": False,
        "submitted_at": None,
        "course_id": 101,
    },
    {
        "id": 4002,
        "name": "Lab 4 Submission",
        "due_at": "2026-04-30T23:59:00Z",
        "points_possible": 35,
        "excused": False,
        "submitted_at": None,
        "course_id": 102,
    },
    {
        # This one is excused — should be filtered out by the tool
        "id": 4003,
        "name": "Excused: Quiz 2",
        "due_at": "2026-04-25T23:59:00Z",
        "points_possible": 15,
        "excused": True,
        "submitted_at": None,
        "course_id": 103,
    },
]

GRADES = [
    {
        "id": 101,
        "name": "ACS 4220 AI Engineering",
        "enrollment_state": "active",
        "enrollments": [{"computed_current_score": 91.5, "computed_final_score": 89.0}],
    },
    {
        "id": 102,
        "name": "ACS 3930 Web APIs",
        "enrollment_state": "active",
        "enrollments": [{"computed_current_score": 84.0, "computed_final_score": 82.5}],
    },
    {
        "id": 103,
        "name": "ACS 3210 Databases",
        "enrollment_state": "active",
        # No grades posted yet — tool must return null, not crash
        "enrollments": [{"computed_current_score": None, "computed_final_score": None}],
    },
]

ANNOUNCEMENTS = [
    {
        "id": 5001,
        "title": "Final Project Demo Day — May 15th",
        "message": "<p>Demo day is <strong>May 15th</strong> at 2pm in Room 204. Bring your laptops and be ready to present for 10 minutes.</p>",
        "posted_at": "2026-05-04T10:00:00Z",
        "context_code": "course_101",
    },
    {
        "id": 5002,
        "title": "Office Hours Cancelled This Friday",
        "message": "<p>No office hours this Friday. Email me if you need help before the deadline.</p>",
        "posted_at": "2026-05-03T09:00:00Z",
        "context_code": "course_102",
    },
]

ASSIGNMENT_DETAIL = {
    "id": 1001,
    "name": "Agent SDK Project",
    "description": "<p>Build a multi-step agentic assistant using the Anthropic SDK. Your agent must use at least 3 tools and handle tool chaining.</p><ul><li>Submit a GitHub repo link</li><li>Include a README with setup instructions</li><li>Demo video (5 min max)</li></ul>",
    "due_at": "2026-05-09T23:59:00Z",
    "points_possible": 100,
    "submission_types": ["online_url", "online_upload"],
    "rubric": [
        {"description": "Tool Implementation", "points": 40},
        {"description": "Multi-step Reasoning", "points": 30},
        {"description": "Code Quality & Tests", "points": 20},
        {"description": "README & Documentation", "points": 10},
    ],
}

ROUTES = {
    "/api/v1/courses/101/assignments": ASSIGNMENTS_101,
    "/api/v1/courses/102/assignments": ASSIGNMENTS_102,
    "/api/v1/courses/103/assignments": ASSIGNMENTS_103,
    "/api/v1/users/self/missing_submissions": MISSING,
    "/api/v1/courses/101/assignments/1001": ASSIGNMENT_DETAIL,
}


class CanvasHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        query = self.path[len(path):]

        # Grade report: /courses with include[]=total_scores param
        if path == "/api/v1/courses" and ("total_scores" in query):
            self._send_json(GRADES)
            return

        # Announcements: /announcements with context_codes[] param
        if path == "/api/v1/announcements":
            self._send_json(ANNOUNCEMENTS)
            return

        # Base /courses (list_courses)
        if path == "/api/v1/courses":
            self._send_json(COURSES)
            return

        if path in ROUTES:
            self._send_json(ROUTES[path])
            return

        print(f"  [404] No route matched: {self.path!r}", flush=True)
        self._send_json({"errors": [{"message": "not found"}]}, status=404)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        status = args[1] if len(args) > 1 else "?"
        print(f"  [{status}] {args[0]}", flush=True)


if __name__ == "__main__":
    port = 8000
    print(f"Fake Canvas server running at http://localhost:{port}")
    print("Make sure your .env has:")
    print(f"  CANVAS_BASE_URL=http://localhost:{port}")
    print(f"  CANVAS_API_TOKEN=demo-token")
    print()
    print("Waiting for requests...")
    HTTPServer(("localhost", port), CanvasHandler).serve_forever()
