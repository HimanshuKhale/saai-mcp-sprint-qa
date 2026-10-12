# SAAI MCP Sprint QA

Minimal evidence repository for the SAAI Applied MCP Engineering Sprint.

## API integration slice

This repository includes a narrow, read-only integration with the public
JSONPlaceholder API. It demonstrates:

- environment-based configuration;
- bounded input validation;
- response-schema validation;
- structured error handling;
- unit tests for success and failure paths;
- an explicit API contract.

## Files

- `api_integration.py` — integration client and MCP-tool-friendly wrapper
- `test_api_integration.py` — unit tests using mocked upstream responses
- `API_CONTRACT.md` — integration contract, boundaries, and failure model
- `.env.example` — non-secret runtime configuration example

## Run

```bash
python -m unittest -v
python api_integration.py
```
