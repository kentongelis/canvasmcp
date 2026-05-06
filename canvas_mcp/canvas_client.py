import os
import re
import httpx
from dotenv import load_dotenv

load_dotenv()


class CanvasClient:
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = (base_url or os.getenv("CANVAS_BASE_URL", "")).rstrip("/")
        self.token = token or os.getenv("CANVAS_API_TOKEN", "")
        self._headers = {"Authorization": f"Bearer {self.token}"}

    async def get(self, path: str, params: dict = None) -> dict | list:
        url = f"{self.base_url}/api/v1{path}"
        async with httpx.AsyncClient() as http:
            response = await http.get(url, headers=self._headers, params=params)

        if response.status_code == 401:
            return {"error": 401, "message": "Unauthorized — check your Canvas API token."}
        if response.status_code == 404:
            return {"error": 404, "message": "Resource not found."}
        if response.status_code == 429:
            return {"error": 429, "message": "Canvas rate limit exceeded. Wait before retrying."}

        response.raise_for_status()
        return response.json()

    async def get_all_pages(self, path: str, params: dict = None) -> list:
        url = f"{self.base_url}/api/v1{path}"
        results = []

        async with httpx.AsyncClient() as http:
            while url:
                response = await http.get(url, headers=self._headers, params=params)

                if response.status_code == 401:
                    return {"error": 401, "message": "Unauthorized — check your Canvas API token."}
                if response.status_code == 404:
                    return {"error": 404, "message": "Resource not found."}
                if response.status_code == 429:
                    return {"error": 429, "message": "Canvas rate limit exceeded. Wait before retrying."}

                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    results.extend(data)
                else:
                    return data

                # Follow Link: rel="next" if present
                link_header = response.headers.get("Link", "")
                next_url = _parse_next_link(link_header)
                url = next_url
                params = None  # next URL already has params baked in

        return results


def _parse_next_link(link_header: str) -> str | None:
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            match = re.search(r"<([^>]+)>", part)
            if match:
                return match.group(1)
    return None
