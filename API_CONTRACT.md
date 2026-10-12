# External API Integration Contract

## Purpose

This QA implementation demonstrates a narrow, read-only external API integration
suitable for exposure through an MCP tool. The client integrates with the public
JSONPlaceholder service and retrieves a single Todo record.

## Operation

`fetch_todo(todo_id: int)`

- Method: `GET`
- Upstream path: `/todos/{todo_id}`
- Authority: read-only
- Input: positive integer `todo_id`
- Output: a normalized JSON object with:
  - `user_id: int`
  - `id: int`
  - `title: str`
  - `completed: bool`

## Validation

The integration rejects:

- non-positive or non-integer identifiers before making a request;
- non-object JSON responses;
- missing or incorrectly typed contract fields;
- non-positive upstream identifiers.

## Failure handling

Upstream failures are converted into bounded application exceptions:

- HTTP failures -> `UpstreamUnavailable`
- network failures -> `UpstreamUnavailable`
- timeout or invalid JSON -> `UpstreamUnavailable`
- contract/schema failures -> `InvalidUpstreamPayload`

Raw credentials, arbitrary URLs, unrestricted methods, and arbitrary upstream
operations are not exposed.

## Configuration

Runtime configuration is provided through environment variables:

- `MCP_EXTERNAL_API_BASE_URL`
- `MCP_EXTERNAL_API_TIMEOUT_SECONDS`

No secrets are required for JSONPlaceholder. If a future provider requires a
credential, it should be supplied through an environment variable and must not
be committed to source control.

## Verification

Run:

```bash
python -m unittest -v
python api_integration.py
```

The unit tests cover the successful contract, schema rejection, HTTP failure
mapping, and input validation.
