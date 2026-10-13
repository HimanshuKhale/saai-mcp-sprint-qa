"""Production-oriented MCP server foundation for the SAAI sprint.

The module keeps protocol registration separate from domain/integration logic:
`MCPApplication` owns the explicit tool boundary and `build_fastmcp_server`
adapts that boundary to the official MCP Python SDK when it is installed.

Core dispatch and validation use only the standard library, which keeps the
boundary independently testable without starting a protocol transport.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from api_integration import IntegrationError, fetch_todo


DEFAULT_SERVER_NAME = "saai-mcp-sprint-qa"

JsonObject = dict[str, Any]
ToolHandler = Callable[[Mapping[str, Any]], JsonObject]
TodoFetcher = Callable[[int], JsonObject]


class ToolError(RuntimeError):
    """Base exception exposed by the bounded tool-dispatch layer."""


class ToolNotFoundError(ToolError):
    """Raised when a client requests a tool that is not explicitly registered."""


class ToolValidationError(ToolError):
    """Raised when tool arguments do not match the declared boundary."""


class ToolExecutionError(ToolError):
    """Raised when an approved tool cannot complete safely."""


@dataclass(frozen=True)
class ServerSettings:
    """Non-secret server settings loaded from environment variables."""

    name: str = DEFAULT_SERVER_NAME

    @classmethod
    def from_env(cls) -> "ServerSettings":
        name = os.getenv("MCP_SERVER_NAME", DEFAULT_SERVER_NAME).strip()
        if not name:
            raise ValueError("MCP_SERVER_NAME must not be blank")
        if len(name) > 80:
            raise ValueError("MCP_SERVER_NAME must be 80 characters or fewer")
        return cls(name=name)


@dataclass(frozen=True)
class ArgumentRule:
    """Small schema rule used before any handler is invoked."""

    expected_type: type
    required: bool = True
    minimum: int | float | None = None

    def validate(self, name: str, value: Any) -> None:
        if self.expected_type is int and isinstance(value, bool):
            raise ToolValidationError(f"{name} must be an integer")
        if not isinstance(value, self.expected_type):
            raise ToolValidationError(
                f"{name} must be {self.expected_type.__name__}"
            )
        if self.minimum is not None and value < self.minimum:
            raise ToolValidationError(f"{name} must be >= {self.minimum}")


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    arguments: Mapping[str, ArgumentRule]
    handler: ToolHandler

    def validate_arguments(self, supplied: Mapping[str, Any]) -> None:
        unknown = sorted(set(supplied) - set(self.arguments))
        if unknown:
            raise ToolValidationError(
                f"Unexpected argument(s): {', '.join(unknown)}"
            )

        for name, rule in self.arguments.items():
            if name not in supplied:
                if rule.required:
                    raise ToolValidationError(f"Missing required argument: {name}")
                continue
            rule.validate(name, supplied[name])


class ToolRegistry:
    """Explicit allow-list for discoverable and dispatchable MCP operations."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if not definition.name or not definition.name.replace("_", "").isalnum():
            raise ValueError("Tool names must be alphanumeric/underscore values")
        if definition.name in self._tools:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._tools[definition.name] = definition

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "arguments": {
                    name: {
                        "type": rule.expected_type.__name__,
                        "required": rule.required,
                        "minimum": rule.minimum,
                    }
                    for name, rule in tool.arguments.items()
                },
            }
            for tool in sorted(self._tools.values(), key=lambda item: item.name)
        ]

    def dispatch(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> JsonObject:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(f"Tool is not registered: {name}")

        supplied = {} if arguments is None else arguments
        if not isinstance(supplied, Mapping):
            raise ToolValidationError("Tool arguments must be an object")

        tool.validate_arguments(supplied)
        result = tool.handler(supplied)
        if not isinstance(result, dict):
            raise ToolExecutionError("Tool returned a non-object response")
        return result


class MCPApplication:
    """Application boundary shared by tests and the MCP transport adapter."""

    def __init__(
        self,
        *,
        settings: ServerSettings | None = None,
        todo_fetcher: TodoFetcher = fetch_todo,
    ) -> None:
        self.settings = settings or ServerSettings.from_env()
        self._todo_fetcher = todo_fetcher
        self.registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self) -> None:
        self.registry.register(
            ToolDefinition(
                name="health",
                description="Return bounded server health and registered-tool metadata.",
                arguments={},
                handler=self._health,
            )
        )
        self.registry.register(
            ToolDefinition(
                name="get_todo",
                description=(
                    "Fetch one Todo record from the approved read-only external API."
                ),
                arguments={
                    "todo_id": ArgumentRule(int, minimum=1),
                },
                handler=self._get_todo,
            )
        )

    def _health(self, _arguments: Mapping[str, Any]) -> JsonObject:
        return {
            "status": "ok",
            "server": self.settings.name,
            "tools": list(self.registry.names()),
        }

    def _get_todo(self, arguments: Mapping[str, Any]) -> JsonObject:
        todo_id = arguments["todo_id"]
        try:
            return self._todo_fetcher(todo_id)
        except IntegrationError as exc:
            # Keep provider URLs, response bodies, credentials, and raw provider
            # exceptions inside the integration boundary.
            raise ToolExecutionError("Approved upstream service request failed") from exc

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> JsonObject:
        return self.registry.dispatch(name, arguments)


def create_application(
    *,
    settings: ServerSettings | None = None,
    todo_fetcher: TodoFetcher = fetch_todo,
) -> MCPApplication:
    """Construct the testable MCP application boundary."""

    return MCPApplication(settings=settings, todo_fetcher=todo_fetcher)


def build_fastmcp_server(application: MCPApplication | None = None):
    """Adapt the bounded application to the official MCP Python SDK.

    Importing the SDK is deferred so the core registry and tests stay runnable
    without transport dependencies. Install `requirements.txt` before starting
    the actual MCP transport.
    """

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "The MCP Python SDK is required to run the protocol server. "
            "Install dependencies with: python -m pip install -r requirements.txt"
        ) from exc

    app = application or create_application()
    server = FastMCP(app.settings.name)

    @server.tool()
    def health() -> JsonObject:
        """Return server health without exposing environment or secret values."""

        return app.call_tool("health")

    @server.tool()
    def get_todo(todo_id: int) -> JsonObject:
        """Retrieve one Todo through the approved read-only integration boundary."""

        return app.call_tool("get_todo", {"todo_id": todo_id})

    return server


def main() -> None:
    """Start the MCP server using the SDK's default stdio transport."""

    build_fastmcp_server().run()


if __name__ == "__main__":
    main()
