from __future__ import annotations

import sqlite3
from uuid import uuid4
from typing import Any

from authlib.integrations.base_client.errors import MismatchingStateError
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request

from app.config import settings


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
    connection = sqlite3.connect(TOKEN_DB_PATH)
    connection.execute(
        """
        create table if not exists auth_tokens (
            token_key text primary key,
            access_token text not null,
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
    if "user_sub" not in columns:
        connection.execute("alter table auth_tokens add column user_sub text")
    if "user_email" not in columns:
        connection.execute("alter table auth_tokens add column user_email text")
    return connection


def get_current_user(request: Request) -> dict[str, Any]:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def maybe_user(request: Request) -> dict[str, Any] | None:
    user = request.session.get("user")
    if isinstance(user, dict):
        return user
    return None


def clear_oidc_state(request: Request) -> None:
    stale_keys = [key for key in request.session.keys() if "_state_oci_" in key]
    for key in stale_keys:
        request.session.pop(key, None)


def store_access_token(request: Request, access_token: str | None) -> None:
    clear_access_token(request)
    if not access_token:
        return
    token_key = str(uuid4())
    user = maybe_user(request) or {}
    user_sub = user.get("sub")
    user_email = user.get("email")
    with _get_connection() as connection:
        connection.execute(
            """
            insert or replace into auth_tokens (token_key, access_token, user_sub, user_email)
            values (?, ?, ?, ?)
            """,
            (token_key, access_token, user_sub, user_email),
        )
    request.session["access_token_key"] = token_key


def get_access_token(request: Request) -> str | None:
    token_key = request.session.get("access_token_key")
    with _get_connection() as connection:
        row = None
        if token_key:
            row = connection.execute(
                "select token_key, access_token from auth_tokens where token_key = ?",
                (token_key,),
            ).fetchone()
        if not row:
            user = maybe_user(request) or {}
            user_sub = user.get("sub")
            user_email = user.get("email")
            if user_sub:
                row = connection.execute(
                    """
                    select token_key, access_token
                    from auth_tokens
                    where user_sub = ?
                    order by rowid desc
                    limit 1
                    """,
                    (user_sub,),
                ).fetchone()
            if not row and user_email:
                row = connection.execute(
                    """
                    select token_key, access_token
                    from auth_tokens
                    where lower(user_email) = lower(?)
                    order by rowid desc
                    limit 1
                    """,
                    (user_email,),
                ).fetchone()
    if not row:
        return None
    request.session["access_token_key"] = str(row[0])
    return str(row[1])


def clear_access_token(request: Request) -> None:
    token_key = request.session.pop("access_token_key", None)
    user = maybe_user(request) or {}
    user_sub = user.get("sub")
    user_email = user.get("email")
    with _get_connection() as connection:
        if token_key:
            connection.execute("delete from auth_tokens where token_key = ?", (token_key,))
        if user_sub:
            connection.execute("delete from auth_tokens where user_sub = ?", (user_sub,))
        elif user_email:
            connection.execute("delete from auth_tokens where lower(user_email) = lower(?)", (user_email,))


__all__ = [
    "MismatchingStateError",
    "clear_access_token",
    "clear_oidc_state",
    "get_access_token",
    "get_current_user",
    "maybe_user",
    "oauth",
    "store_access_token",
]
