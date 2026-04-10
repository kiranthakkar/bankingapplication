from __future__ import annotations

from agents import function_tool

from app.data import data_store


@function_tool
def get_customer_overview() -> dict:
    """Return the demo customer's profile summary and high-level account snapshot."""
    return data_store.get_customer_summary()


@function_tool
def list_accounts() -> list[dict]:
    """Return all deposit and credit accounts for the demo customer."""
    return data_store.list_accounts()


@function_tool
def get_account_details(account_id_or_name: str) -> dict:
    """Look up one account by account ID, product name, or kind such as checking or savings."""
    account = data_store.get_account(account_id_or_name)
    if not account:
        return {"success": False, "message": f"Account '{account_id_or_name}' was not found."}
    return {"success": True, "account": account}


@function_tool
def get_recent_transactions(account_id_or_name: str, limit: int = 5) -> dict:
    """Return the most recent transactions for a specific account."""
    transactions = data_store.recent_transactions(account_id_or_name, limit=limit)
    if not transactions:
        return {"success": False, "message": f"No account matched '{account_id_or_name}'."}
    return {"success": True, "transactions": transactions}


@function_tool
def list_cards() -> list[dict]:
    """Return the customer's linked debit and credit cards."""
    return data_store.list_cards()


@function_tool
def report_card_issue(card_id: str, issue_type: str) -> dict:
    """Report a lost, stolen, or suspicious card issue and update the card status."""
    return data_store.report_card_issue(card_id, issue_type)


@function_tool
def transfer_between_accounts(
    from_account_id: str,
    to_account_id: str,
    amount: float,
    memo: str = "",
) -> dict:
    """Transfer money between demo accounts using exact account IDs."""
    return data_store.transfer(from_account_id, to_account_id, amount, memo)
