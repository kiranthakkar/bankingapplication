"""Persistent SQL MCP client used by the banking data layer.

This helper binds to the app's long-lived SQLcl MCP session, ensures the saved
connection is established, and normalizes CSV tool output into Python rows.
"""

from __future__ import annotations

import csv
import io
from asyncio import Lock
from typing import Any

from agents.mcp import MCPServer, MCPServerManager

from app.config import settings


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize CSV row keys to lowercase and trim surrounding whitespace."""
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, str):
            normalized[str(key).lower()] = value.strip()
        else:
            normalized[str(key).lower()] = value
    return normalized


class SQLMCPClient:
    """Wrap a shared SQLcl MCP session for reusable database access."""

    def __init__(self) -> None:
        self._server: MCPServer | None = None
        self._lock = Lock()
        self._connected = False

    async def bind_manager(self, manager: MCPServerManager | None) -> None:
        """Bind this client to the SQLcl server from the shared MCP manager."""
        server: MCPServer | None = None
        if manager is not None:
            for candidate in manager.active_servers:
                if getattr(candidate, "name", None) == "sqlcl":
                    server = candidate
                    break
        async with self._lock:
            self._server = server
            self._connected = False

    async def connect(self) -> None:
        """Open the saved SQLcl connection for subsequent tool calls."""
        async with self._lock:
            await self._connect_locked()

    async def disconnect(self) -> None:
        """Disconnect the saved SQLcl connection if it is currently open."""
        async with self._lock:
            if self._server is None or not self._connected:
                self._connected = False
                return
            await self._server.call_tool("disconnect", {"model": self._model_name})
            self._connected = False

    async def run_query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a SQL query and return the CSV result as normalized rows."""
        result = await self._call_tool(
            "run-sql",
            {
                "sql": sql.rstrip(";"),
                "model": self._model_name,
                "executionType": "SYNCHRONOUS",
            },
        )
        text = self._result_text(result).strip()
        if not text:
            return []
        return self._parse_csv_rows(text)

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        async with self._lock:
            await self._connect_locked()
            if self._server is None:
                raise RuntimeError("The SQL MCP server is not available.")

            result = await self._server.call_tool(tool_name, arguments)
            detail = self._result_text(result)
            if result.isError and self._looks_disconnected(detail):
                self._connected = False
                await self._connect_locked()
                result = await self._server.call_tool(tool_name, arguments)
                detail = self._result_text(result)

            if result.isError:
                detail = detail or f"The SQL MCP tool '{tool_name}' returned an error."
                raise RuntimeError(detail)
            return result

    async def _connect_locked(self) -> None:
        if self._connected:
            return
        if self._server is None:
            raise RuntimeError("The SQL MCP server is not configured for this application.")

        result = await self._server.call_tool(
            "connect",
            {
                "connection_name": settings.sqlcl_connection_name,
                "model": self._model_name,
            },
        )
        detail = self._result_text(result)
        if result.isError:
            raise RuntimeError(detail or "Failed to connect to the SQL MCP server.")
        self._connected = True

    @property
    def _model_name(self) -> str:
        return settings.model or "bankingapplication"

    @staticmethod
    def _result_text(result: Any) -> str:
        parts: list[str] = []
        for content_item in getattr(result, "content", []) or []:
            text_value = getattr(content_item, "text", None)
            if text_value:
                parts.append(text_value)
        return "\n".join(parts).strip()

    @staticmethod
    def _looks_disconnected(detail: str) -> bool:
        normalized = detail.strip().lower()
        return "connection not established" in normalized or "not connected" in normalized

    @staticmethod
    def _parse_csv_rows(payload: str) -> list[dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(payload))
        if not reader.fieldnames:
            return []
        rows: list[dict[str, Any]] = []
        for row in reader:
            if row is None:
                continue
            normalized = _normalize_row({key: value for key, value in row.items() if key is not None})
            if not any(str(value or "").strip() for value in normalized.values()):
                continue
            rows.append(normalized)
        return rows


sql_mcp_client = SQLMCPClient()
