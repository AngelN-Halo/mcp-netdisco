# mcn-netdisco

MCP server for querying a Netdisco instance over its HTTP API.

## Configuration

Set:

- `NETDISCO_URL` — base URL, for example `http://netdisco:5000`
- `NETDISCO_TOKEN` — optional bearer token
- `NETDISCO_TIMEOUT` — request timeout in seconds (default: 20)

## Run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
export NETDISCO_URL=http://localhost:5000
python -m mcn_netdisco
```

The server exposes the `netdisco_api` tool, which accepts a read-only API path and optional query parameters. It blocks absolute URLs and non-GET methods.
