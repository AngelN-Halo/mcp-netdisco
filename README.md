# mcp-netdisco

A Dockerized, read-only OpenAPI gateway that gives Open WebUI access to Netdisco.

## Features

- OpenAPI integration for Open WebUI
- Bearer protection using `MCPO_API_KEY`
- Automatic Netdisco `/login` using username/password
- Automatic Netdisco API-key renewal and retry after HTTP 401
- IP, MAC, hostname, switch, and router lookup
- Cisco MAC normalization, such as `9cf6.1a86.0e0c` to `9c:f6:1a:86:0e:0c`
- Partial MAC matching
- IP-to-MAC-to-switch-port resolution
- Switch-port configuration enrichment

## Configuration

Create a `.env` file:

```env
NETDISCO_URL=http://your-netdisco-server:5000
NETDISCO_USERNAME=your-netdisco-username
NETDISCO_PASSWORD=your-netdisco-password
MCPO_API_KEY=replace-with-a-long-random-secret
NETDISCO_TIMEOUT=20
```

Never commit `.env`. The Netdisco credentials are used only to obtain an upstream API key.

## Docker and Nginx Proxy Manager

The Compose service joins the external Docker network named `proxy` and exposes port `8000` only inside that network.

```bash
docker compose up -d --build
```

Configure Nginx Proxy Manager with:

```text
Forward Hostname: mcp-netdisco
Forward Port: 8000
Scheme: http
```

Add the resulting HTTPS URL to Open WebUI as an **OpenAPI** connection and use `MCPO_API_KEY` as its bearer token.

The schema is available at `/openapi.json`.

## Preferred lookup

Use `lookup_identifier` for normal searches. It accepts:

- IPv4 addresses
- Full or partial MAC addresses
- IEEE MAC format: `9c:f6:1a:86:0e:0c`
- Cisco MAC format: `9cf6.1a86.0e0c`
- Hostnames
- Managed switch or router names and addresses

The response includes endpoint records, managed-device matches, switch-port sightings, and port configuration. Port details include fields returned by Netdisco such as interface description/name, VLAN/PVID, admin and operational state, speed, duplex, MTU, MAC, neighbor information, and timestamps.

To keep broad partial searches bounded, the gateway enriches at most 20 matching MAC addresses and 25 unique switch ports. The response sets `results_truncated` when a query exceeds either limit.

## Other endpoints

- `GET /lookup` — preferred universal lookup
- `GET /find-node` — endpoint IP/MAC lookup with port enrichment
- `GET /find-device` — managed switches and routers only
- `GET /device/{ip}` — details for a known managed switch or router
- `GET /health` — unauthenticated health check

## Security

All data endpoints require:

```http
Authorization: Bearer <MCPO_API_KEY>
```

The service is read-only and does not publish its container port directly on the Docker host.

## License

No license has been selected yet.
