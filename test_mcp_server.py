import os
import unittest
from unittest.mock import patch

from api_integration import UpstreamUnavailable
from mcp_server import (
    MCPApplication,
    ServerSettings,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)


class MCPApplicationTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def fake_fetch(todo_id):
            self.calls.append(todo_id)
            return {
                "user_id": 3,
                "id": todo_id,
                "title": "Protocol boundary",
                "completed": False,
            }

        self.app = MCPApplication(
            settings=ServerSettings(name="qa-mcp"),
            todo_fetcher=fake_fetch,
        )

    def test_registers_only_explicit_tools(self):
        self.assertEqual(self.app.registry.names(), ("get_todo", "health"))

    def test_health_reports_server_and_registered_tools(self):
        result = self.app.call_tool("health")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["server"], "qa-mcp")
        self.assertEqual(result["tools"], ["get_todo", "health"])

    def test_get_todo_validates_and_dispatches(self):
        result = self.app.call_tool("get_todo", {"todo_id": 11})

        self.assertEqual(self.calls, [11])
        self.assertEqual(result["id"], 11)
        self.assertEqual(result["title"], "Protocol boundary")

    def test_invalid_identifier_is_rejected_before_handler(self):
        with self.assertRaises(ToolValidationError):
            self.app.call_tool("get_todo", {"todo_id": 0})

        self.assertEqual(self.calls, [])

    def test_boolean_is_not_accepted_as_integer(self):
        with self.assertRaises(ToolValidationError):
            self.app.call_tool("get_todo", {"todo_id": True})

        self.assertEqual(self.calls, [])

    def test_missing_argument_is_rejected(self):
        with self.assertRaises(ToolValidationError):
            self.app.call_tool("get_todo", {})

    def test_unexpected_argument_is_rejected(self):
        with self.assertRaises(ToolValidationError):
            self.app.call_tool(
                "get_todo",
                {"todo_id": 1, "url": "https://evil.test"},
            )

    def test_unregistered_tool_is_rejected(self):
        with self.assertRaises(ToolNotFoundError):
            self.app.call_tool("shell", {"command": "whoami"})

    def test_upstream_details_are_bounded_at_protocol_boundary(self):
        def failing_fetch(_todo_id):
            raise UpstreamUnavailable(
                "provider leaked details: https://internal.example"
            )

        app = MCPApplication(
            settings=ServerSettings(name="qa-mcp"),
            todo_fetcher=failing_fetch,
        )

        with self.assertRaisesRegex(
            ToolExecutionError,
            "^Approved upstream service request failed$",
        ):
            app.call_tool("get_todo", {"todo_id": 1})

    @patch.dict(os.environ, {"MCP_SERVER_NAME": "configured-mcp"}, clear=False)
    def test_server_name_comes_from_environment(self):
        settings = ServerSettings.from_env()
        self.assertEqual(settings.name, "configured-mcp")


if __name__ == "__main__":
    unittest.main()
