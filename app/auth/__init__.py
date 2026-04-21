"""Authentication helpers for OCI Identity Domain sign-in flows.

This module centralizes OAuth client registration, session user resolution, and
persisted access-token handling for downstream authenticated MCP calls.
"""

from __future__ import annotations

import logging
import sqlite3
from uuid import uuid4
from typing import Any

from authlib.integrations.base_client.errors import MismatchingStateError
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request

from app.config import settings


logger = logging.getLogger(__name__)
oauth = OAuth()
oauth.register(
    name="oci",
    server_metadata_url=settings.oidc_discovery_url,
    client_id=settings.oidc_client_id,
    client_secret=settings.oidc_client_secret,
    client_kwargs={"scope": settings.oidc_scopes},
)

TOKEN_DB_PATH = settings.runtime_dir / "auth_tokens.db"
TOKEN_DB_PATH.parent.mkdir(exist_ok=True)


def _get_connection() -> sqlite3.Connection:
    """Return the SQLite connection used to store session-bound bearer tokens."""
    logger.debug("Opening auth token SQLite database at %s", TOKEN_DB_PATH)
    connection = sqlite3.connect(TOKEN_DB_PATH)
    connection.execute(
        """
        create table if not exists auth_tokens (
            token_key text primary key,
            access_token text not null,
            session_binding text,
            user_sub text,
            user_email text
        )
        """
    )
    columns = {
        str(row[1])
        for row in connection.execute("pragma table_info(auth_tokens)").fetchall()
        if len(row) > 1
    }
    if "session_binding" not in columns:
        connection.execute("alter table auth_tokens add column session_binding text")
    if "user_sub" not in columns:
        connection.execute("alter table auth_tokens add column user_sub text")
    if "user_email" not in columns:
        connection.execute("alter table auth_tokens add column user_email text")
    if "id_token" not in columns:
        connection.execute("alter table auth_tokens add column id_token text")
    return connection


def get_current_user(request: Request) -> dict[str, Any]:
    """Return the authenticated session user or raise ``401`` when absent."""
    user = request.session.get("user")
    if not user:
        logger.info("Rejected unauthenticated request for path=%s", request.url.path)
        raise HTTPException(status_code=401, detail="Authentication required.")
    logger.debug(
        "Resolved authenticated session user for path=%s sub=%s email=%s",
        request.url.path,
        user.get("sub"),
        user.get("email"),
    )
    return user


def maybe_user(request: Request) -> dict[str, Any] | None:
    """Return the session user when present, otherwise ``None``."""
    user = request.session.get("user")
    if isinstance(user, dict):
        return user
    return None


def clear_oidc_state(request: Request) -> None:
    """Remove stale OIDC state entries left in the session store."""
    stale_keys = [key for key in request.session.keys() if "_state_oci_" in key]
    if stale_keys:
        logger.debug("Clearing %s stale OIDC state entries", len(stale_keys))
    for key in stale_keys:
        request.session.pop(key, None)


def store_access_token(
    request: Request,
    access_token: str | None,
    id_token: str | None = None,
) -> None:
    """Persist the latest bearer token and bind it to the current web session."""
    clear_access_token(request)
    if not access_token:
        logger.info("No access token available to store for current session.")
        return
    token_key = str(uuid4())
    session_binding = str(uuid4())
    user = maybe_user(request) or {}
    user_sub = user.get("sub")
    user_email = user.get("email")
    with _get_connection() as connection:
        connection.execute(
            """
            insert or replace into auth_tokens
                (token_key, access_token, session_binding, user_sub, user_email, id_token)
            values (?, ?, ?, ?, ?, ?)
            """,
            (token_key, access_token, session_binding, user_sub, user_email, id_token),
        )
    request.session["access_token_key"] = token_key
    request.session["access_token_binding"] = session_binding
    logger.info(
        "Stored access token for session-bound user sub=%s email=%s",
        user_sub,
        user_email,
    )


def get_id_token(request: Request) -> str | None:
    """Return the id_token associated with the current browser session."""
    token_key = request.session.get("access_token_key")
    session_binding = request.session.get("access_token_binding")
    with _get_connection() as connection:
        row = None
        if token_key:
            row = connection.execute(
                "select id_token from auth_tokens where token_key = ?",
                (token_key,),
            ).fetchone()
        if not row and session_binding:
            row = connection.execute(
                "select id_token from auth_tokens where session_binding = ? order by rowid desc limit 1",
                (session_binding,),
            ).fetchone()
    if row:
        return str(row[0]) if row[0] else None
    return None


def get_access_token(request: Request) -> str | None:
    """Return the bearer token associated with the current browser session."""
    token_key = request.session.get("access_token_key")
    session_binding = request.session.get("access_token_binding")
    with _get_connection() as connection:
        row = None
        if token_key:
            row = connection.execute(
                "select token_key, access_token, session_binding from auth_tokens where token_key = ?",
                (token_key,),
            ).fetchone()
        if not row and session_binding:
            row = connection.execute(
                """
                select token_key, access_token, session_binding
                from auth_tokens
                where session_binding = ?
                order by rowid desc
                limit 1
                """,
                (session_binding,),
            ).fetchone()
    if not row:
        logger.debug("No persisted access token found for current session.")
        return None
    request.session["access_token_key"] = str(row[0])
    request.session["access_token_binding"] = str(row[2])
    logger.debug("Resolved persisted access token for current session.")
    return str(row[1])


def clear_access_token(request: Request) -> None:
    """Delete the persisted access token associated with the current session."""
    token_key = request.session.pop("access_token_key", None)
    session_binding = request.session.pop("access_token_binding", None)
    with _get_connection() as connection:
        if token_key:
            connection.execute("delete from auth_tokens where token_key = ?", (token_key,))
        if session_binding:
            connection.execute("delete from auth_tokens where session_binding = ?", (session_binding,))
    if token_key or session_binding:
        logger.info("Cleared persisted access token for current session.")


__all__ = [
    "MismatchingStateError",
    "clear_access_token",
    "clear_oidc_state",
    "get_access_token",
    "get_current_user",
    "get_id_token",
    "maybe_user",
    "oauth",
    "store_access_token",
]
