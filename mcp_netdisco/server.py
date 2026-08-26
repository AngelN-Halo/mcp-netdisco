import asyncio
import os
import re
import time
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

app = FastAPI(
    title="Netdisco OpenAPI Gateway",
    description="Read-only Netdisco lookup tools for Open WebUI. Use lookup_identifier for IP, MAC, hostname, switch, or router searches.",
    version="0.4.0",
)
bearer_scheme = HTTPBearer(auto_error=False)
_token: str | None = None
_token_issued_at = 0.0
TOKEN_REFRESH_SECONDS = 30 * 24 * 60 * 60
MAX_MAC_EXPANSIONS = 20
MAX_PORT_DETAILS = 25


def _base_url() -> str:
    return os.environ.get("NETDISCO_URL", "http://cenetbox-ls01.leanderisd.org:5000").strip().rstrip("/")


def _credentials() -> tuple[str, str]:
    username = os.environ.get("NETDISCO_USERNAME", "").strip()
    password = os.environ.get("NETDISCO_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("NETDISCO_USERNAME and NETDISCO_PASSWORD are required")
    return username, password


def _normalize_node_query(query: str) -> str:
    value = query.strip()
    if not re.fullmatch(r"[0-9A-Fa-f.:-]+", value):
        return value
    compact = re.sub(r"[.:-]", "", value)
    looks_like_mac = "." in value or ":" in value or "-" in value or len(compact) == 12
    if looks_like_mac and 2 <= len(compact) <= 12 and len(compact) % 2 == 0 and re.fullmatch(r"[0-9A-Fa-f]+", compact):
        return ":".join(compact[index:index + 2] for index in range(0, len(compact), 2)).lower()
    return value


async def require_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> None:
    expected = os.environ.get("MCPO_API_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="MCPO_API_KEY is not configured")
    if credentials is None or credentials.scheme.lower() != "bearer" or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


async def _login(client: httpx.AsyncClient) -> str:
    global _token, _token_issued_at
    username, password = _credentials()
    response = await client.post(f"{_base_url()}/login", auth=(username, password), headers={"Accept": "application/json"})
    response.raise_for_status()
    token = response.json().get("api_key")
    if not token:
        raise RuntimeError("Netdisco login response did not contain api_key")
    _token, _token_issued_at = token, time.time()
    return token


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    timeout = float(os.environ.get("NETDISCO_TIMEOUT", "20"))
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        token = await _login(client) if _token is None or time.time() - _token_issued_at >= TOKEN_REFRESH_SECONDS else _token
        response = await client.get(f"{_base_url()}{path}", params=params or {}, headers={"Accept": "application/json", "Authorization": token})
        if response.status_code == 401:
            token = await _login(client)
            response = await client.get(f"{_base_url()}{path}", params=params or {}, headers={"Accept": "application/json", "Authorization": token})
        response.raise_for_status()
        return response.json()


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return HTTPException(status_code=502 if status >= 500 else status, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


def _macs_from_result(result: dict[str, Any]) -> list[str]:
    macs: set[str] = set()
    for section in ("macs", "ips", "sightings"):
        for row in result.get(section, []) or []:
            if row.get("mac"):
                macs.add(row["mac"])
    return sorted(macs)


async def _safe_port_detail(switch: str, port: str) -> dict[str, Any]:
    path = f"/api/v1/object/device/{quote(switch, safe='')}/port/{quote(port, safe='')}"
    try:
        configuration = await _get(path)
        return {"switch": switch, "port": port, "configuration": configuration}
    except Exception as exc:
        return {"switch": switch, "port": port, "error": str(exc)}


async def _enriched_node_search(query: str, partial: bool, include_port_details: bool) -> dict[str, Any]:
    normalized = _normalize_node_query(query)
    search_params = {"q": normalized, "partial": partial, "deviceports": True, "show_vendor": True}
    primary = await _get("/api/v1/search/node", search_params)

    macs = _macs_from_result(primary)
    expanded: list[dict[str, Any]] = []
    for mac in macs[:MAX_MAC_EXPANSIONS]:
        if normalized.lower() == mac.lower() and primary.get("sightings"):
            continue
        detail = await _get("/api/v1/search/node", {"q": mac, "partial": False, "deviceports": True, "show_vendor": True})
        expanded.append({"mac": mac, "results": detail})

    sightings: list[dict[str, Any]] = list(primary.get("sightings", []) or [])
    for item in expanded:
        sightings.extend(item["results"].get("sightings", []) or [])

    unique_ports: list[tuple[str, str]] = []
    seen_ports: set[tuple[str, str]] = set()
    for sighting in sightings:
        key = (str(sighting.get("switch", "")), str(sighting.get("port", "")))
        if all(key) and key not in seen_ports:
            seen_ports.add(key)
            unique_ports.append(key)

    port_details: list[dict[str, Any]] = []
    if include_port_details:
        port_details = await asyncio.gather(*(_safe_port_detail(switch, port) for switch, port in unique_ports[:MAX_PORT_DETAILS]))

    return {
        "input_query": query,
        "normalized_query": normalized,
        "partial_match": partial,
        "node_results": primary,
        "expanded_mac_results": expanded,
        "switch_port_sightings": sightings,
        "port_details": port_details,
        "limits": {
            "mac_expansions": MAX_MAC_EXPANSIONS,
            "port_details": MAX_PORT_DETAILS,
            "results_truncated": len(macs) > MAX_MAC_EXPANSIONS or len(unique_ports) > MAX_PORT_DETAILS,
        },
    }


@app.get("/health", summary="Health check", operation_id="health_check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/lookup",
    summary="Look up any IP, MAC, hostname, switch, or router with switch-port details",
    description="Preferred tool for all lookups. Accepts Cisco MAC notation such as 9cf6.1a86.0e0c, normalizes it to 9c:f6:1a:86:0e:0c, supports partial matching, and returns switch-port sightings plus port configuration.",
    operation_id="lookup_identifier",
    dependencies=[Depends(require_api_key)],
)
async def lookup(
    query: str = Query(..., description="IP, full or partial MAC in Cisco/IEEE format, hostname, switch, or router"),
    partial: bool = Query(True, description="Enable Netdisco partial matching"),
    include_port_details: bool = Query(True, description="Fetch configuration for matching switch ports"),
) -> Any:
    try:
        nodes = await _enriched_node_search(query, partial, include_port_details)
        devices = await _get("/api/v1/search/device", {"q": query})
        return {
            **nodes,
            "device_results": devices,
            "guidance": "node_results and switch_port_sightings describe endpoints; device_results describes managed switches/routers; port_details contains switch-port configuration.",
        }
    except Exception as exc:
        raise _error(exc) from exc


@app.get(
    "/find-node",
    summary="Find an endpoint by IP or MAC with switch-port details",
    description="Endpoint search supporting Cisco MAC normalization, partial matching, switch-port sightings, and port configuration.",
    operation_id="find_endpoint_node",
    dependencies=[Depends(require_api_key)],
)
async def find_node(
    query: str = Query(..., description="Endpoint IP or full/partial MAC in Cisco or IEEE format"),
    partial: bool = Query(True, description="Enable Netdisco partial matching"),
    include_port_details: bool = Query(True, description="Fetch configuration for matching switch ports"),
) -> Any:
    try:
        return await _enriched_node_search(query, partial, include_port_details)
    except Exception as exc:
        raise _error(exc) from exc


@app.get(
    "/find-device",
    summary="Find a managed switch or router",
    description="Search only Netdisco-managed infrastructure devices. Do not use for ordinary endpoint/client IP or MAC addresses.",
    operation_id="find_managed_network_device",
    dependencies=[Depends(require_api_key)],
)
async def find_device(query: str = Query(..., description="Managed switch/router IP, DNS name, or name")) -> Any:
    try:
        return await _get("/api/v1/search/device", {"q": query})
    except Exception as exc:
        raise _error(exc) from exc


@app.get(
    "/device/{ip}",
    summary="Get details for a known managed switch or router",
    description="Use only after finding a managed device. Returns 404 for endpoint/client IP addresses.",
    operation_id="get_managed_device_details",
    dependencies=[Depends(require_api_key)],
)
async def device(ip: str) -> Any:
    try:
        return await _get(f"/api/v1/object/device/{ip}")
    except Exception as exc:
        raise _error(exc) from exc


def main() -> None:
    import uvicorn

    uvicorn.run("mcp_netdisco.server:app", host=os.environ.get("API_HOST", "0.0.0.0"), port=int(os.environ.get("API_PORT", "8000")))
