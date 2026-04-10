from __future__ import annotations

from agents.mcp import MCPServerManager

from app.mcp.ocios import build_ocios_server
from app.mcp.sql import build_sqlcl_server


def build_mcp_manager() -> MCPServerManager | None:
    servers = [server for server in (build_sqlcl_server(),) if server is not None]
    if not servers:
        return None
    return MCPServerManager(servers, strict=False)


__all__ = ["build_mcp_manager", "build_ocios_server", "build_sqlcl_server"]
