# mcp-netdisco

A Dockerized [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that gives MCP clients read-only access to Netdisco.

## Features

- Uses Netdisco's `/login` endpoint with HTTP Basic credentials
- Caches the returned API key and refreshes it every 30 days
- Automatically re-authenticates if Netdisco returns HTTP 401
- Restricts requests to relative paths on the configured Netdisco server
- Runs over MCP stdio for clients that launch Docker containers

## Configuration

Create a `.env` file. The default URL is the production Netdisco server:

```env
NETDISCO_URL=http://your-url-site.com:5000
NETDISCO_USERNAME=your-netdisco-username
NETDISCO_PASSWORD=your-netdisco-password
NETDISCO_TIMEOUT=20
```

The username and password are used only to obtain an API key from `POST /login`. Do not commit `.env`.

## Docker

Build and run directly:

```bash
docker build -t mcp-netdisco .
docker run --rm -i --env-file .env mcp-netdisco
```

Or use Compose:

```bash
docker compose build
docker compose run --rm -T mcp-netdisco
```

## MCP tool

The server exposes:

`netdisco_api(path, query)`

- `path`: a relative Netdisco API path, such as `/api/v1/search/device`
- `query`: optional query-string parameters

Only HTTP GET requests are supported for data calls. Absolute URLs are rejected, and requests cannot redirect to another host.

## Netdisco token lifetime

The server refreshes its cached API key every 30 days and retries once after a 401 response. Netdisco's `api_token_lifetime` setting must be longer than the refresh interval (or the 401 retry will obtain a fresh key when needed). The refresh interval can later be made configurable if needed.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
export NETDISCO_USERNAME=your-user
export NETDISCO_PASSWORD=your-password
python -m mcp_netdisco
```

## License

No license has been selected yet.
