import os
import re
import httpx
from dotenv import load_dotenv

load_dotenv()

_RATE_LIMIT_MESSAGE = "Canvas rate limit exceeded. Wait before retrying."

_ERROR_MESSAGES = {
    401: "Unauthorized — check your Canvas API token.",
    403: "Forbidden — your institution or instructor has not given you access to this Canvas data.",
    404: "Resource not found.",
    429: _RATE_LIMIT_MESSAGE,
}


class CanvasClient:
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = (base_url or os.getenv("CANVAS_BASE_URL", "")).rstrip("/")
        self.token = token or os.getenv("CANVAS_API_TOKEN", "")
        self._headers = {"Authorization": f"Bearer {self.token}"}

    async def get(self, path: str, params: dict = None) -> dict | list:
        config_error = self._config_error()
        if config_error:
            return config_error

        url = f"{self.base_url}/api/v1{path}"
        try:
            async with httpx.AsyncClient() as http:
                response = await http.get(url, headers=self._headers, params=params)
        except httpx.RequestError as exc:
            return _connection_error(exc)

        return _parse_response(response)

    async def get_all_pages(self, path: str, params: dict = None) -> list:
        config_error = self._config_error()
        if config_error:
            return config_error

        url = f"{self.base_url}/api/v1{path}"
        params = {"per_page": 100, **(params or {})}
        results = []

        try:
            async with httpx.AsyncClient() as http:
                while url:
                    response = await http.get(url, headers=self._headers, params=params)
                    data = _parse_response(response)
                    if isinstance(data, list):
                        results.extend(data)
                    else:
                        # Error dict or non-list payload
                        return data

                    # Follow Link: rel="next" if present
                    link_header = response.headers.get("Link", "")
                    next_url = _parse_next_link(link_header)
                    url = next_url
                    params = None  # next URL already has params baked in
        except httpx.RequestError as exc:
            return _connection_error(exc)

        return results

    def _config_error(self) -> dict | None:
        if not self.base_url:
            return {"error": "config", "message": "CANVAS_BASE_URL is not set. Add it to your .env file."}
        if not self.token:
            return {"error": "config", "message": "CANVAS_API_TOKEN is not set. Add it to your .env file."}
        return None


def _parse_response(response: httpx.Response) -> dict | list:
    status = response.status_code
    if not response.is_success:
        # Canvas throttles with 403 + "Rate Limit Exceeded" rather than 429
        if status == 403 and "rate limit" in response.text.lower():
            return {"error": status, "message": _RATE_LIMIT_MESSAGE}
        if status in _ERROR_MESSAGES:
            return {"error": status, "message": _ERROR_MESSAGES[status]}
        if status >= 500:
            return {"error": status, "message": f"Canvas server error ({status}). Try again later."}
        return {"error": status, "message": f"Canvas request failed with status {status}."}

    try:
        return response.json()
    except ValueError:
        return {
            "error": "invalid_response",
            "message": "Canvas returned a non-JSON response — check that CANVAS_BASE_URL points to your Canvas instance.",
        }


def _connection_error(exc: httpx.RequestError) -> dict:
    return {
        "error": "connection",
        "message": f"Could not reach Canvas ({type(exc).__name__}). Check CANVAS_BASE_URL and your network connection.",
    }


def _parse_next_link(link_header: str) -> str | None:
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            match = re.search(r"<([^>]+)>", part)
            if match:
                return match.group(1)
    return None
