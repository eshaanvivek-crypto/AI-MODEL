from __future__ import annotations

import requests


class PageFetcher:
    def __init__(self, timeout: int, user_agent: str) -> None:
        self.timeout = timeout
        self.user_agent = user_agent

    def fetch(self, url: str) -> str:
        resp = requests.get(url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            raise ValueError("Unsupported content type")
        return resp.text
