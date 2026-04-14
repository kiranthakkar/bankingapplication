"""SQLcl MCP server construction helpers for the banking application."""

from __future__ import annotations

import logging
from pathlib import Path

from agents.mcp import MCPServerStdio

from app.config import settings


logger = logging.getLogger(__name__)


def _resolve_sqlcl_command() -> str:
    """Resolve the SQLcl executable path from the configured environment."""
    raw_path = settings.sqlcl_path
    if raw_path is None:
        raise ValueError("SQLCL_PATH is required when SQLcl MCP is enabled.")

    sqlcl_path = Path(raw_path).expanduser()
    if sqlcl_path.is_dir():
        sqlcl_path = sqlcl_path / "sql"
    return str(sqlcl_path)


def _resolve_sqlcl_args() -> list[str]:
    """Return the SQLcl arguments required to start in MCP mode."""
    args = list(settings.sqlcl_mcp_args)
    if "-name" not in args and settings.sqlcl_connection_name:
        args.extend(["-name", settings.sqlcl_connection_name])
    return args


def build_sqlcl_server() -> MCPServerStdio | None:
    """Return the SQLcl stdio MCP server when SQLcl is enabled."""
    if not settings.sqlcl_enabled:
        logger.info("SQLcl MCP server is disabled because SQLcl configuration is incomplete.")
        return None

    logger.info(
        "Building SQLcl MCP server for connection=%s command=%s",
        settings.sqlcl_connection_name,
        _resolve_sqlcl_command(),
    )
    logger.debug("SQLcl MCP args=%s", _resolve_sqlcl_args())
    return MCPServerStdio(
        name="sqlcl",
        cache_tools_list=True,
        params={
            "command": _resolve_sqlcl_command(),
            "args": _resolve_sqlcl_args(),
        },
    )
