import os
import time
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

app = FastAPI(
    title="Netdisco OpenAPI Gateway",
    description="Read-only Netdisco lookup tools for Open WebUI. Use lookup_identifier for normal IP, MAC, hostname, switch, or router searches.",
    version="0.3.0",
)
bearer_scheme = HTTPBearer(auto_error=False)
_token: str | None = None
_token_issued_at = 0.0
TOKEN_REFRESH_SECONDS = 30 * 24 * 60 * 60


def _base_url() -> str:
    return os.environ.get("NETDISCO_URL", "http://cenetbox-ls01.leanderisd.org:5000").strip().rstrip("/")


def _credentials() -> tuple[str, str]:
    username = os.environ.get("NETDISCO_USERNAME", "").strip()
    password = os.environ.get("NETDISCO_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("NETDISCO_USERNAME and NETDISCO_PASSWORD are required")
    return username, password


async def require_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> None:
    expected = os.environ.get("MCPO_API_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="MCPO_API_KEY is not configured")
    if credentials is None or credentials.scheme.lower() != "bearer" or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


async def _login(client: httpx.AsyncClient) -> str:
    global _token, _token_issued_at
    username, password = _credentials()
    response = await client.post(
        f"{_base_url()}/login",
        auth=(username, password),
        headers={"Accept": "application/json"},
    )
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
        response = await client.get(
            f"{_base_url()}{path}",
            params=params or {},
            headers={"Accept": "application/json", "Authorization": token},
        )
        if response.status_code == 401:
            token = await _login(client)
            response = await client.get(
                f"{_base_url()}{path}",
                params=params or {},
                headers={"Accept": "application/json", "Authorization": token},
            )
        response.raise_for_status()
        return response.json()


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return HTTPException(status_code=502 if status >= 500 else status, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


@app.get("/health", summary="Health check", operation_id="health_check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/lookup",
    summary="Look up any IP address, MAC address, hostname, switch, or router",
    description="Preferred general lookup tool. Searches both endpoint/node records and managed network devices. Use this first for any IP or MAC address.",
    operation_id="lookup_identifier",
    dependencies=[Depends(require_api_key)],
)
async def lookup(query: str = Query(..., description="IP address, MAC address, hostname, switch name, or router name")) -> Any:
    try:
        nodes = await _get("/api/v1/search/node", {"q": query})
        devices = await _get("/api/v1/search/device", {"q": query})
        return {
            "query": query,
            "node_results": nodes,
            "device_results": devices,
            "guidance": "node_results contains endpoint IP/MAC sightings; device_results contains managed switches and routers.",
        }
    except Exception as exc:
        raise _error(exc) from exc


@app.get(
    "/find-node",
    summary="Find an endpoint by IP or MAC",
    description="Search endpoint/node records, including computers, phones, printers, and other client IP or MAC addresses.",
    operation_id="find_endpoint_node",
    dependencies=[Depends(require_api_key)],
)
async def find_node(query: str = Query(..., description="Endpoint IP address or MAC address")) -> Any:
    try:
        return await _get("/api/v1/search/node", {"q": query})
    except Exception as exc:
        raise _error(exc) from exc


@app.get(
    "/find-device",
    summary="Find a managed switch or router",
    description="Search only Netdisco-managed infrastructure devices. Do not use this for ordinary endpoint/client IP addresses or MAC addresses.",
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
    description="Retrieve details only after a managed device was found. This endpoint returns 404 for endpoint/client IP addresses.",
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

    uvicorn.run(
        "mcp_netdisco.server:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", "8000")),
    )
