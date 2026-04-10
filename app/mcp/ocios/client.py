from __future__ import annotations

from agents.mcp import MCPServerStreamableHttp

from app.auth import get_access_token
from app.config import settings


def build_ocios_server(access_token: str | None = None, request=None) -> MCPServerStreamableHttp | None:
    if not settings.ocios_mcp_enabled:
        return None
    if access_token is None and request is not None:
        access_token = get_access_token(request)
    if not access_token:
        return None

    return MCPServerStreamableHttp(
        name="ocios",
        cache_tools_list=True,
        client_session_timeout_seconds=30,
        params={
            "url": settings.ocios_mcp_url,
            "headers": {"Authorization": f"Bearer {access_token}"},
            "timeout": 300,
            "sse_read_timeout": 300,
        },
    )
