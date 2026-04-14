"""Agent tool implementations backed by the banking data service.

These tools are registered with the OpenAI Agents SDK and provide the model
with safe, application-scoped access to customer banking information.
"""

from __future__ import annotations

from agents import function_tool

from app.data import data_store


DEFAULT_SUGGESTED_PROMPTS = [
    "Show me all my account balances.",
    "What are my most recent checking transactions?",
    "Transfer $200 from CHK-001 to SAV-001 for my vacation fund.",
    "Freeze my debit card.",
]


@function_tool
async def get_customer_overview() -> dict:
    """Return the authenticated customer's profile summary and high-level account snapshot."""
    return await data_store.get_customer_summary()


@function_tool
async def fetch_bootstrap_view() -> dict:
    """Return the exact bootstrap payload consumed by the home page."""
    return {
        "customer_summary": await data_store.get_customer_summary(),
        "suggested_prompts": list(DEFAULT_SUGGESTED_PROMPTS),
    }


@function_tool
async def list_accounts() -> list[dict]:
    """Return all deposit and credit accounts for the authenticated customer."""
    return await data_store.list_accounts()


@function_tool
async def fetch_accounts_view() -> dict:
    """Return the exact accounts payload consumed by the accounts tab."""
    return {"accounts": await data_store.list_accounts()}


@function_tool
async def get_account_details(account_id_or_name: str) -> dict:
    """Look up one account by account ID, product name, or kind such as checking or savings."""
    account = await data_store.get_account(account_id_or_name)
    if not account:
        return {"success": False, "message": f"Account '{account_id_or_name}' was not found."}
    return {"success": True, "account": account}


@function_tool
async def get_recent_transactions(account_id_or_name: str, limit: int = 5) -> dict:
    """Return the most recent transactions for a specific account."""
    transactions = await data_store.recent_transactions(account_id_or_name, limit=limit)
    if not transactions:
        return {"success": False, "message": f"No account matched '{account_id_or_name}'."}
    return {"success": True, "transactions": transactions}


@function_tool
async def list_cards() -> list[dict]:
    """Return the customer's linked debit and credit cards."""
    return await data_store.list_cards()


@function_tool
async def fetch_cards_view() -> dict:
    """Return the exact cards payload consumed by the cards tab."""
    return {"cards": await data_store.list_cards()}


@function_tool
async def fetch_recent_activity_view(limit: int = 6) -> dict:
    """Return the exact recent-activity payload consumed by the activity tab."""
    return {"recent_activity": await data_store.recent_activity(limit=limit)}


@function_tool
async def report_card_issue(card_id: str, issue_type: str) -> dict:
    """Report a lost, stolen, or suspicious card issue and update the card status."""
    return await data_store.report_card_issue(card_id, issue_type)


@function_tool
async def transfer_between_accounts(
    from_account_id: str,
    to_account_id: str,
    amount: float,
    memo: str = "",
) -> dict:
    """Transfer money between accounts using exact account IDs."""
    return await data_store.transfer(from_account_id, to_account_id, amount, memo)
