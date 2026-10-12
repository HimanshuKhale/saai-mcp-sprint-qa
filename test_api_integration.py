import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from api_integration import (
    InvalidUpstreamPayload,
    JsonPlaceholderClient,
    UpstreamUnavailable,
)


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._body = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class JsonPlaceholderClientTests(unittest.TestCase):
    def setUp(self):
        self.client = JsonPlaceholderClient(
            base_url="https://example.test/",
            timeout=1.0,
        )

    @patch("api_integration.urlopen")
    def test_fetch_todo_validates_and_returns_typed_result(self, mocked_urlopen):
        mocked_urlopen.return_value = _FakeResponse(
            {
                "userId": 7,
                "id": 11,
                "title": "Verify MCP integration",
                "completed": False,
            }
        )

        todo = self.client.fetch_todo(11)

        self.assertEqual(todo.id, 11)
        self.assertEqual(todo.user_id, 7)
        self.assertEqual(todo.title, "Verify MCP integration")
        self.assertFalse(todo.completed)

    @patch("api_integration.urlopen")
    def test_invalid_payload_is_rejected(self, mocked_urlopen):
        mocked_urlopen.return_value = _FakeResponse(
            {
                "userId": 7,
                "id": "11",
                "title": "Wrong type",
                "completed": False,
            }
        )

        with self.assertRaises(InvalidUpstreamPayload):
            self.client.fetch_todo(11)

    @patch("api_integration.urlopen")
    def test_http_failure_is_mapped_to_bounded_error(self, mocked_urlopen):
        mocked_urlopen.side_effect = HTTPError(
            url="https://example.test/todos/11",
            code=503,
            msg="Unavailable",
            hdrs=None,
            fp=None,
        )

        with self.assertRaises(UpstreamUnavailable):
            self.client.fetch_todo(11)

    def test_invalid_identifier_is_rejected_before_network_call(self):
        with self.assertRaises(ValueError):
            self.client.fetch_todo(0)


if __name__ == "__main__":
    unittest.main()
