# SAAI MCP Sprint QA

Evidence repository for the SAAI Applied MCP Engineering Sprint.

## Current implementation

The repository now has two deliberately separated layers:

1. **External integration** — a bounded, read-only JSONPlaceholder client.
2. **MCP server foundation** — an explicit tool registry/dispatch boundary with
   validation, safe failure handling, and an adapter to the official MCP Python SDK.

This keeps provider/network details outside the protocol boundary and makes the
core application testable without starting an MCP transport.

## MCP tools

The current server exposes only explicitly registered operations:

- `health` — returns bounded server health and tool metadata.
- `get_todo(todo_id)` — validates a positive integer and delegates to the
  approved read-only integration.

Arbitrary URLs, arbitrary HTTP methods, shell commands, filesystem access, and
dynamic tool registration are not exposed.

## Repository structure

- `mcp_server.py` — MCP application boundary, validation, dispatch, and FastMCP adapter
- `test_mcp_server.py` — protocol-boundary and failure-path unit tests
- `api_integration.py` — validated external API client
- `test_api_integration.py` — external-integration unit tests
- `MCP_SERVER.md` — architecture, trust boundaries, configuration, and verification
- `API_CONTRACT.md` — external API contract and failure model
- `.env.example` — non-secret runtime configuration example
- `requirements.txt` — MCP transport dependency

## Setup

Python 3.12+ is recommended.

```bash
python -m venv .venv
```

Activate the environment, then install the MCP SDK:

```bash
python -m pip install -r requirements.txt
```

Configuration is supplied through environment variables. Copy values from
`.env.example` into your local environment; do not commit real credentials.

## Verify

The deterministic unit-test suite does not make live upstream calls:

```bash
python -m unittest -v
```

The API client can also be exercised directly:

```bash
python api_integration.py
```

## Run the MCP server

```bash
python mcp_server.py
```

The SDK starts its default stdio transport. The transport adapter exposes only
the tools declared by `MCPApplication`.

## Scope

This commit establishes the core MCP protocol and repository foundation. Richer
domain tools, broader schemas, deployment hardening, and full acceptance tests
belong to later sprint tasks.
