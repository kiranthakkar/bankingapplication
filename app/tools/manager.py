"""Manager-only agent tools for bank analytics and reporting."""

from __future__ import annotations

from agents import function_tool

from app.data import data_store


@function_tool
async def list_all_customers(page: int = 1, page_size: int = 50) -> dict:
    """Return a paginated list of all bank customers for manager review."""
    customers = await data_store.list_all_customers(page=page, page_size=page_size)
    return {"customers": customers, "page": page, "page_size": page_size, "count": len(customers)}


@function_tool
async def get_most_active_accounts(limit: int = 10, days: int = 30) -> dict:
    """Return the accounts with the most transactions in the last N days."""
    accounts = await data_store.get_most_active_accounts(limit=min(limit, 50), days=days)
    return {"accounts": accounts, "days": days}


@function_tool
async def get_dormant_accounts(days_inactive: int = 90, limit: int = 20) -> dict:
    """Return accounts with no transaction activity in the last N days."""
    accounts = await data_store.get_dormant_accounts(days_inactive=days_inactive, limit=min(limit, 100))
    return {"accounts": accounts, "days_inactive": days_inactive}


@function_tool
async def get_premium_customers() -> dict:
    """Return all customers on Gold, Platinum, or Premium tiers with their balances."""
    customers = await data_store.get_premium_customers()
    return {"customers": customers, "count": len(customers)}


@function_tool
async def get_analytics_summary() -> dict:
    """Return aggregate KPIs: total customers, accounts, transactions, deposits, and premium customers."""
    return await data_store.get_analytics_summary()
