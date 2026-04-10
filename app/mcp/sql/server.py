from __future__ import annotations

from pathlib import Path

from agents.mcp import MCPServerManager, MCPServerStdio

from app.config import settings


def _resolve_sqlcl_command() -> str:
    raw_path = settings.sqlcl_path
    if raw_path is None:
        raise ValueError("SQLCL_PATH is required when SQLcl MCP is enabled.")

    sqlcl_path = Path(raw_path).expanduser()
    if sqlcl_path.is_dir():
        sqlcl_path = sqlcl_path / "sql"
    return str(sqlcl_path)


def _resolve_sqlcl_args() -> list[str]:
    args = list(settings.sqlcl_mcp_args)
    if "-name" not in args and settings.sqlcl_connection_name:
        args.extend(["-name", settings.sqlcl_connection_name])
    return args


def build_sqlcl_server() -> MCPServerStdio | None:
    if not settings.sqlcl_enabled:
        return None

    return MCPServerStdio(
        name="sqlcl",
        cache_tools_list=True,
        params={
            "command": _resolve_sqlcl_command(),
            "args": _resolve_sqlcl_args(),
        },
    )


def build_sqlcl_manager() -> MCPServerManager | None:
    server = build_sqlcl_server()
    if server is None:
        return None
    return MCPServerManager([server], strict=False)
