import json
import os
import time
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-netdisco")
_token: str | None = None
_token_issued_at = 0.0
TOKEN_REFRESH_SECONDS = 30 * 24 * 60 * 60


def _base_url() -> str:
    value = os.environ.get(
        "NETDISCO_URL",
        "http://cenetbox-ls01.leanderisd.org:5000",
    ).strip().rstrip("/")
    if not value:
        raise ValueError("NETDISCO_URL is not configured")
    return value


def _credentials() -> tuple[str, str]:
    username = os.environ.get("NETDISCO_USERNAME", "").strip()
    password = os.environ.get("NETDISCO_PASSWORD", "")
    if not username or not password:
        raise ValueError(
            "NETDISCO_USERNAME and NETDISCO_PASSWORD are required"
        )
    return username, password


async def _login(client: httpx.AsyncClient) -> str:
    global _token, _token_issued_at
    username, password = _credentials()
    response = await client.post(
        f"{_base_url()}/login",
        auth=(username, password),
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("api_key")
    if not token:
        raise RuntimeError("Netdisco login response did not contain api_key")
    _token = token
    _token_issued_at = time.time()
    return token


async def _get_token(client: httpx.AsyncClient) -> str:
    if _token is None or time.time() - _token_issued_at >= TOKEN_REFRESH_SECONDS:
        return await _login(client)
    return _token


@mcp.tool()
async def netdisco_api(
    path: str,
    query: dict[str, Any] | None = None,
) -> str:
    """Read Netdisco data using a relative GET API path.

    Examples: /api/v1/search/device, /api/v1/device, /api/v1/port.
    """
    if not path.startswith("/") or path.startswith("//") or "://" in path:
        raise ValueError("path must be a relative API path beginning with '/'")

    timeout = float(os.environ.get("NETDISCO_TIMEOUT", "20"))
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        token = await _get_token(client)
        response = await client.get(
            f"{_base_url()}{path}",
            params=query or {},
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401:
            token = await _login(client)
            response = await client.get(
                f"{_base_url()}{path}",
                params=query or {},
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        if "application/json" in response.headers.get("content-type", ""):
            return json.dumps(response.json(), indent=2, default=str)
        return response.text


def main() -> None:
    mcp.run()
