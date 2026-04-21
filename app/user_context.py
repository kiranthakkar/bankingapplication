"""Context-local authenticated user helpers for async agent execution.

The agent tool layer runs outside the FastAPI request object, so this module
stores the current authenticated user in a context variable for downstream
Oracle and tool lookups.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any


_current_user: ContextVar[dict[str, Any] | None] = ContextVar("current_user", default=None)


def get_authenticated_user() -> dict[str, Any] | None:
    """Return the authenticated user bound to the current async context."""
    return _current_user.get()


@asynccontextmanager
async def authenticated_user_scope(user: dict[str, Any]):
    """Temporarily bind the authenticated user for nested async operations."""
    token = _current_user.set(user)
    try:
        yield
    finally:
        _current_user.reset(token)
