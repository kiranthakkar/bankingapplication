"""Group-based authorization helpers."""

from __future__ import annotations

from fastapi import Depends, HTTPException

from app.auth import get_current_user

BANK_MANAGER_GROUP = "bank-manager"


def get_user_groups(user: dict | None) -> list[str]:
    if not user:
        return []
    groups = user.get("groups") or []
    if isinstance(groups, str):
        return [groups]
    return list(groups)


def is_bank_manager(user: dict | None) -> bool:
    return BANK_MANAGER_GROUP in get_user_groups(user)


def require_bank_manager(user: dict = Depends(get_current_user)) -> dict:
    """Raise 403 unless the authenticated user belongs to the bank-manager group."""
    if not is_bank_manager(user):
        raise HTTPException(status_code=403, detail="Access restricted to bank managers.")
    return user
