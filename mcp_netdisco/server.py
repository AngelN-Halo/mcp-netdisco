import json
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-netdisco")


def _base_url() -> str:
    value = os.environ.get("NETDISCO_URL", "").strip().rstrip("/")
    if not value:
        raise ValueError("NETDISCO_URL is not configured")
    return value


def _headers() -> dict[str, str]:
    token = os.environ.get("NETDISCO_TOKEN", "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


@mcp.tool()
async def netdisco_api(
    path: str,
    query: dict[str, Any] | None = None,
) -> str:
    """Read Netdisco data using a relative GET API path.

    Examples: /api/node, /api/device, /api/port.
    """
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("path must be a relative API path beginning with '/'")
    if "://" in path:
        raise ValueError("absolute URLs are not allowed")
    url = f"{_base_url()}{path}"
    timeout = float(os.environ.get("NETDISCO_TIMEOUT", "20"))
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        response = await client.get(url, params=query or {}, headers=_headers())
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            payload: Any = response.json()
            return json.dumps(payload, indent=2, default=str)
        return response.text


def main() -> None:
    mcp.run()
