from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from threading import Lock
from uuid import uuid4

from app.models.domain import Account, Card, Customer, Transaction


class BankingRepository:
    """In-memory demo data store for one sample customer."""

    def __init__(self) -> None:
        today = date.today()
        checking = Account(
            id="CHK-001",
            name="Everyday Checking",
            kind="checking",
            balance=4825.17,
            routing_last4="1107",
            account_last4="2048",
        )
        savings = Account(
            id="SAV-001",
            name="Rainy Day Savings",
            kind="savings",
            balance=12540.80,
            routing_last4="1107",
            account_last4="7711",
            apr=4.15,
        )
        credit = Account(
            id="CRD-001",
            name="Travel Rewards Card",
            kind="credit",
            balance=642.18,
            account_last4="9184",
            available_credit=7357.82,
        )

        checking.transactions = [
            Transaction("txn-1001", checking.id, today - timedelta(days=1), "Payroll Deposit", 3200.00, "income"),
            Transaction("txn-1002", checking.id, today - timedelta(days=2), "City Power Utility", -124.33, "utilities"),
            Transaction("txn-1003", checking.id, today - timedelta(days=4), "Farmers Market", -63.42, "groceries"),
            Transaction("txn-1004", checking.id, today - timedelta(days=6), "Transfer to Savings", -500.00, "transfer"),
        ]
        savings.transactions = [
            Transaction("txn-2001", savings.id, today - timedelta(days=6), "Transfer from Checking", 500.00, "transfer"),
            Transaction("txn-2002", savings.id, today - timedelta(days=25), "Interest Credit", 38.77, "interest"),
        ]
        credit.transactions = [
            Transaction("txn-3001", credit.id, today - timedelta(days=1), "SkyJet Airlines", 318.94, "travel"),
            Transaction("txn-3002", credit.id, today - timedelta(days=3), "Blue Bottle Coffee", 14.25, "dining"),
            Transaction("txn-3003", credit.id, today - timedelta(days=8), "Payment Received", -250.00, "payment"),
        ]

        self._customer = Customer(
            id="CUS-001",
            full_name="Jordan Lee",
            email="jordan.lee@examplebank.demo",
            tier="Premier",
        )
        self._accounts = {
            checking.id: checking,
            savings.id: savings,
            credit.id: credit,
        }
        self._cards = {
            "CARD-001": Card(
                id="CARD-001",
                name="Debit Card",
                network="Visa",
                last4="4832",
                status="active",
                linked_account_id=checking.id,
            ),
            "CARD-002": Card(
                id="CARD-002",
                name="Travel Rewards Card",
                network="Visa Signature",
                last4="9184",
                status="active",
                linked_account_id=credit.id,
            ),
        }
        self._lock = Lock()

    def get_customer_summary(self) -> dict:
        total_deposits = sum(
            account.balance for account in self._accounts.values() if account.kind != "credit"
        )
        credit_balance = next(
            account.balance for account in self._accounts.values() if account.kind == "credit"
        )
        return {
            "customer": asdict(self._customer),
            "snapshot": {
                "total_deposit_balances": round(total_deposits, 2),
                "credit_card_balance": round(credit_balance, 2),
                "linked_accounts": len(self._accounts),
            },
        }

    def list_accounts(self) -> list[dict]:
        return [self._serialize_account(account) for account in self._accounts.values()]

    def get_account(self, account_id_or_name: str) -> dict | None:
        normalized = account_id_or_name.strip().lower()
        for account in self._accounts.values():
            if normalized in {
                account.id.lower(),
                account.name.lower(),
                account.kind.lower(),
            }:
                return self._serialize_account(account)
        return None

    def recent_transactions(self, account_id_or_name: str, limit: int = 5) -> list[dict]:
        account = self._resolve_account(account_id_or_name)
        if not account:
            return []
        txns = sorted(account.transactions, key=lambda txn: txn.posted_on, reverse=True)
        return [self._serialize_transaction(txn) for txn in txns[:limit]]

    def list_cards(self) -> list[dict]:
        return [asdict(card) for card in self._cards.values()]

    def recent_activity(self, limit: int = 6) -> list[dict]:
        activity: list[tuple[date, dict]] = []
        for account in self._accounts.values():
            for txn in account.transactions:
                payload = self._serialize_transaction(txn)
                payload["account_id"] = account.id
                payload["account_name"] = account.name
                activity.append((txn.posted_on, payload))

        activity.sort(key=lambda item: item[0], reverse=True)
        return [payload for _, payload in activity[:limit]]

    def dashboard_data(self) -> dict:
        return {
            "accounts": self.list_accounts(),
            "cards": self.list_cards(),
            "recent_activity": self.recent_activity(),
        }

    def report_card_issue(self, card_id: str, issue_type: str) -> dict:
        with self._lock:
            card = self._cards.get(card_id)
            if not card:
                return {"success": False, "message": f"Card {card_id} was not found."}
            if issue_type.lower() in {"lost", "stolen"}:
                card.status = "reported_stolen"
            else:
                card.status = "frozen"
            return {
                "success": True,
                "message": f"{card.name} ending in {card.last4} is now marked as {card.status}.",
            }

    def transfer(self, from_account_id: str, to_account_id: str, amount: float, memo: str = "") -> dict:
        with self._lock:
            if amount <= 0:
                return {"success": False, "message": "Transfer amount must be greater than zero."}

            source = self._accounts.get(from_account_id)
            destination = self._accounts.get(to_account_id)

            if not source or not destination:
                return {"success": False, "message": "One or both account IDs were not found."}
            if source.id == destination.id:
                return {"success": False, "message": "Source and destination accounts must be different."}
            if source.kind == "credit":
                return {"success": False, "message": "This demo only supports transfers out of deposit accounts."}
            if source.balance < amount:
                return {"success": False, "message": "Insufficient funds in the source account."}

            source.balance = round(source.balance - amount, 2)
            if destination.kind == "credit":
                destination.balance = round(destination.balance - amount, 2)
                if destination.available_credit is not None:
                    destination.available_credit = round(destination.available_credit + amount, 2)
            else:
                destination.balance = round(destination.balance + amount, 2)

            today = date.today()
            suffix = uuid4().hex[:8]
            outbound_description = f"Transfer to {destination.name}"
            inbound_description = f"Transfer from {source.name}"
            if memo:
                outbound_description = f"{outbound_description} ({memo})"
                inbound_description = f"{inbound_description} ({memo})"

            source.transactions.insert(
                0,
                Transaction(f"txn-out-{suffix}", source.id, today, outbound_description, -amount, "transfer"),
            )
            destination.transactions.insert(
                0,
                Transaction(f"txn-in-{suffix}", destination.id, today, inbound_description, amount if destination.kind != "credit" else -amount, "transfer"),
            )

            return {
                "success": True,
                "message": f"Transferred ${amount:,.2f} from {source.name} to {destination.name}.",
                "from_account": self._serialize_account(source),
                "to_account": self._serialize_account(destination),
            }

    def _resolve_account(self, account_id_or_name: str) -> Account | None:
        normalized = account_id_or_name.strip().lower()
        for account in self._accounts.values():
            if normalized in {
                account.id.lower(),
                account.name.lower(),
                account.kind.lower(),
            }:
                return account
        return None

    @staticmethod
    def _serialize_transaction(txn: Transaction) -> dict:
        return {
            "id": txn.id,
            "posted_on": txn.posted_on.isoformat(),
            "description": txn.description,
            "amount": round(txn.amount, 2),
            "category": txn.category,
        }

    def _serialize_account(self, account: Account) -> dict:
        payload = {
            "id": account.id,
            "name": account.name,
            "kind": account.kind,
            "balance": round(account.balance, 2),
            "currency": account.currency,
            "routing_last4": account.routing_last4,
            "account_last4": account.account_last4,
            "apr": account.apr,
            "available_credit": account.available_credit,
        }
        return payload


repository = BankingRepository()
