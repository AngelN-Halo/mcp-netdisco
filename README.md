# mcp-netdisco

A Dockerized [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that gives MCP clients read-only access to a Netdisco server.

## Features

- Exposes a `netdisco_api` tool for Netdisco HTTP API requests
- Restricts requests to relative paths on the configured Netdisco server
- Supports optional bearer-token authentication
- Runs over MCP stdio, making it suitable for clients that launch Docker containers

## Configuration

Create a `.env` file:

```env
NETDISCO_URL=http://netdisco:5000
NETDISCO_TOKEN=
NETDISCO_TIMEOUT=20
```

`NETDISCO_URL` is required. `NETDISCO_TOKEN` is optional and is sent as a bearer token.

## Docker

Build the image:

```bash
docker build -t mcp-netdisco .
```

Run it directly:

```bash
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

- `path`: a relative Netdisco API path such as `/api/node`, `/api/device`, or `/api/port`
- `query`: optional query-string parameters

Only HTTP GET requests are supported. Absolute URLs are rejected, and requests cannot redirect to another host.

## Development

Run locally with Python 3.11+:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
export NETDISCO_URL=http://localhost:5000
python -m mcp_netdisco
```

## License

No license has been selected yet.
