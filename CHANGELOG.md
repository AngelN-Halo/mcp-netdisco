# Changelog

All notable changes to this project are documented here. Commit hashes refer to the Git history on `main`.

## 0.4.0 - 2026-08-26

### Added

- Cisco MAC-address normalization, including `9cf6.1a86.0e0c` to `9c:f6:1a:86:0e:0c` (`d671244`).
- Partial MAC matching using Netdisco's supported `partial` search parameter (`d671244`).
- Automatic IP-to-MAC expansion followed by MAC-to-switch-port sighting lookup (`d671244`).
- Switch-port configuration enrichment through Netdisco's device-port object endpoint (`d671244`).
- Port enrichment fields including interface description/name, VLAN/PVID, admin and operational state, speed, duplex, MTU, MAC, neighbor data, and timestamps (`d671244`).
- Safety limits of 20 expanded MACs and 25 enriched ports per request, with `results_truncated` signaling (`d671244`).

### Fixed

- Empty Netdisco node-search arrays now produce clean no-match responses instead of gateway errors (`6408c44`).
- README replaced stale stdio/MCP instructions with current OpenAPI, bearer-auth, proxy-network, and enriched-lookup documentation (`1cde2d3`).

## 0.3.0 - 2026-08-26

### Added

- Preferred `lookup_identifier` OpenAPI operation for IP, MAC, hostname, switch, and router searches (`2e89185`).
- Clear operation IDs and descriptions so Open WebUI distinguishes endpoint/node searches from managed-device searches (`2e89185`).
- External Docker `proxy` network integration for Nginx Proxy Manager (`a403655`).

### Changed

- Removed direct host port publishing. The service now exposes port 8000 only to containers on the external `proxy` network (`a403655`).

## 0.2.1 - 2026-08-26

### Fixed

- Completed the migration from `APIKeyHeader` to HTTP bearer authentication (`5f46719`).
- Aligned the gateway secret variable with the SolarWinds convention: `MCPO_API_KEY` (`393b1df`, `2de0ee3`).
- Fixed bearer scheme comparison and startup/runtime authentication errors (`8d0573e`).
- Updated upstream Netdisco authorization to use the plain generated API key required by this installed Netdisco version (`f77eef4`).

## 0.2.0 - 2026-08-26

### Added

- FastAPI/OpenAPI gateway for Open WebUI (`b46cecb`).
- Bearer-protected read-only endpoints for node search, device search, managed-device details, and health checks (`b46cecb`).
- Automatic Netdisco login via `POST /login` using HTTP Basic credentials (`d314214`).
- In-memory Netdisco API-key caching, scheduled renewal, and re-login after HTTP 401 (`d314214`).

### Security

- `.env` remains ignored and untracked. Netdisco credentials and gateway bearer values are runtime-only (`b46cecb`).

## 0.1.0 - 2026-08-26

### Added

- Initial read-only Netdisco MCP server scaffold (`a25bf3c`).
- Corrected project/package naming from `mcn-netdisco` to `mcp-netdisco` (`fe23f11`).
- Dockerfile, Compose configuration, and container build (`1d126fc`).
- Initial GitHub documentation and repository metadata (`82532ba`).
