"""Top-level MCP integration helpers for the banking application."""

from __future__ import annotations

import logging

from agents.mcp import MCPServerManager

from app.mcp.ocios import build_ocios_server
from app.mcp.sql import build_sqlcl_server


logger = logging.getLogger(__name__)


def build_mcp_manager() -> MCPServerManager | None:
    """Build the shared MCP manager used by the FastAPI lifespan hook."""
    servers = [server for server in (build_sqlcl_server(),) if server is not None]
    if not servers:
        logger.info("No shared MCP servers configured for application startup.")
        return None
    logger.info(
        "Building shared MCP manager with servers=%s",
        [getattr(server, "name", "unknown") for server in servers],
    )
    return MCPServerManager(servers, strict=False)


__all__ = ["build_mcp_manager", "build_ocios_server", "build_sqlcl_server"]
