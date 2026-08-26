# mcp-netdisco

Dockerized MCP server for querying a Netdisco instance over its HTTP API.

## Configuration

Create a `.env` file:

```env
NETDISCO_URL=http://netdisco:5000
NETDISCO_TOKEN=
NETDISCO_TIMEOUT=20
```

`NETDISCO_URL` is required. The token is optional and is sent as a bearer token.

## Run with Docker Compose

```bash
docker compose build
docker compose run --rm -T mcp-netdisco
```

The container runs the MCP server over stdio, which is suitable for an MCP client that launches the container.

## Run directly

```bash
docker build -t mcp-netdisco .
docker run --rm -i --env-file .env mcp-netdisco
```

The server exposes the `netdisco_api` tool, which accepts a read-only API path and optional query parameters. It blocks absolute URLs and non-GET methods.
# mcp-netdisco
