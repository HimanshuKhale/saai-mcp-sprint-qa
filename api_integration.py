"""Small, production-oriented external API integration used for SAAI QA.

The client intentionally uses only Python's standard library so the repository
can be executed without installing third-party packages.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://jsonplaceholder.typicode.com/"
DEFAULT_TIMEOUT_SECONDS = 5.0


class IntegrationError(RuntimeError):
    """Base class for integration failures."""


class UpstreamUnavailable(IntegrationError):
    """Raised when the upstream service cannot be reached or returns an error."""


class InvalidUpstreamPayload(IntegrationError):
    """Raised when the upstream response does not match the expected contract."""


@dataclass(frozen=True)
class Todo:
    user_id: int
    id: int
    title: str
    completed: bool


class JsonPlaceholderClient:
    """Narrow client exposing one bounded read-only integration operation."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        configured_base = base_url or os.getenv("MCP_EXTERNAL_API_BASE_URL") or DEFAULT_BASE_URL
        self.base_url = configured_base.rstrip("/") + "/"
        self.timeout = timeout or float(
            os.getenv("MCP_EXTERNAL_API_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
        )

    def fetch_todo(self, todo_id: int) -> Todo:
        if not isinstance(todo_id, int) or isinstance(todo_id, bool) or todo_id <= 0:
            raise ValueError("todo_id must be a positive integer")

        endpoint = urljoin(self.base_url, f"todos/{todo_id}")
        request = Request(
            endpoint,
            headers={
                "Accept": "application/json",
                "User-Agent": "saai-mcp-sprint-qa/1.0",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise UpstreamUnavailable(f"Unexpected upstream status: {status}")
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise UpstreamUnavailable(f"Upstream HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise UpstreamUnavailable("Unable to connect to upstream API") from exc
        except (TimeoutError, json.JSONDecodeError) as exc:
            raise UpstreamUnavailable("Upstream response could not be consumed") from exc

        return self._validate_todo(payload)

    @staticmethod
    def _validate_todo(payload: Any) -> Todo:
        if not isinstance(payload, dict):
            raise InvalidUpstreamPayload("Expected a JSON object")

        required = {
            "userId": int,
            "id": int,
            "title": str,
            "completed": bool,
        }
        for key, expected_type in required.items():
            value = payload.get(key)
            if not isinstance(value, expected_type):
                raise InvalidUpstreamPayload(
                    f"Field {key!r} must be {expected_type.__name__}"
                )

        if payload["id"] <= 0 or payload["userId"] <= 0:
            raise InvalidUpstreamPayload("Identifier fields must be positive")

        return Todo(
            user_id=payload["userId"],
            id=payload["id"],
            title=payload["title"].strip(),
            completed=payload["completed"],
        )


def fetch_todo(todo_id: int) -> dict[str, Any]:
    """MCP-tool-friendly wrapper returning a JSON-serializable result."""

    todo = JsonPlaceholderClient().fetch_todo(todo_id)
    return {
        "user_id": todo.user_id,
        "id": todo.id,
        "title": todo.title,
        "completed": todo.completed,
    }


if __name__ == "__main__":
    print(json.dumps(fetch_todo(1), indent=2))
