# MCP Server Foundation

## Purpose

This layer establishes a production-oriented MCP server boundary without
allowing the protocol client to invoke arbitrary application behavior.

The implementation intentionally separates:

- **protocol transport** — provided by the official MCP Python SDK (`FastMCP`);
- **tool registry and dispatch** — owned by `MCPApplication`;
- **external integration** — owned by `api_integration.py`.

That separation keeps validation and authorization boundaries testable even when
no MCP transport is running.

## Architecture

```text
MCP Client
    |
    | MCP / stdio
    v
FastMCP adapter
    |
    v
MCPApplication
    |
    +--> explicit ToolRegistry
    |       |
    |       +--> health
    |       |
    |       +--> get_todo
    |
    +--> input validation
    |
    v
api_integration.fetch_todo
    |
    | HTTPS GET only
    v
JSONPlaceholder
```

## Registration and dispatch

`ToolRegistry` is an explicit allow-list.

A tool cannot be called unless it is registered. Registration rejects duplicate
tool names, and dispatch rejects unknown tools before any handler executes.

Each tool declares argument rules. The registry validates:

- required arguments;
- unexpected arguments;
- expected Python types;
- numeric minimums;
- `bool` values passed where an integer is required.

Handlers are invoked only after those checks pass.

## Current tools

### `health`

Input: none.

Returns bounded status metadata:

```json
{
  "status": "ok",
  "server": "saai-mcp-sprint-qa",
  "tools": ["get_todo", "health"]
}
```

It does not return process environment, filesystem details, credentials, or
network configuration.

### `get_todo`

Input:

```json
{
  "todo_id": 1
}
```

Rules:

- `todo_id` must be an integer;
- booleans are rejected even though `bool` subclasses `int` in Python;
- the identifier must be at least 1;
- no extra URL or method parameter is accepted.

The handler delegates to the existing validated, read-only integration layer.

## Trust and security boundary

The MCP client is treated as untrusted input.

The server therefore:

- exposes only registered tools;
- performs schema-like validation before dispatch;
- does not expose shell execution;
- does not expose arbitrary URLs or HTTP methods;
- does not expose arbitrary filesystem operations;
- keeps external API configuration in environment variables;
- does not require or commit credentials for the current public provider;
- converts integration failures into a bounded protocol-facing error.

The original integration exception is retained as the Python exception cause for
local debugging, while its provider-specific message is not returned as the
public tool error.

## Configuration

Non-secret server configuration:

- `MCP_SERVER_NAME`

External-integration configuration:

- `MCP_EXTERNAL_API_BASE_URL`
- `MCP_EXTERNAL_API_TIMEOUT_SECONDS`

If a future provider requires a credential, it must be supplied outside source
control through the runtime environment or a managed secret store.

## Verification

Run:

```bash
python -m unittest -v
```

The tests verify:

- explicit tool registration;
- health dispatch;
- valid Todo dispatch;
- missing and unexpected argument rejection;
- invalid identifier rejection before handler execution;
- rejection of boolean identifiers;
- rejection of unregistered tools;
- bounded upstream errors;
- environment-based server naming.

The integration test suite separately verifies upstream contract validation and
HTTP failure handling.

## Current limitations

This foundation intentionally does not yet implement:

- authentication between multiple MCP users;
- per-user authorization scopes;
- rate limiting;
- production telemetry;
- network transport hardening;
- the full planned 3–5 domain tools.

Those are later sprint concerns and are not hidden behind the current protocol
surface.
