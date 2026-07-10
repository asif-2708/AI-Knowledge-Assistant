import httpx

from .tools import DOCUMENT_SEARCH_TOOL, SUMMARIZATION_TOOL


class MCPClient:
    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.Client(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def search(self, query: str) -> list[str]:
        response = self.client.post(
            f"{self.base_url}/mcp/search",
            json={"query": query},
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json().get("chunks", [])

    def summarize(self, text: str) -> str:
        response = self.client.post(
            f"{self.base_url}/mcp/summarize",
            json={"text": text},
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json().get("summary", "")
