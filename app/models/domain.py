"""Dataclass domain models used by the banking application."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass
class Transaction:
    """Represents one posted banking transaction."""
    id: str
    account_id: str
    posted_on: date
    description: str
    amount: float
    category: str


@dataclass
class Account:
    """Represents a banking account and its key display attributes."""
    id: str
    name: str
    kind: Literal["checking", "savings", "credit"]
    balance: float
    currency: str = "USD"
    routing_last4: str | None = None
    account_last4: str | None = None
    apr: float | None = None
    available_credit: float | None = None
    transactions: list[Transaction] = field(default_factory=list)


@dataclass
class Card:
    """Represents a debit or credit card linked to a customer."""
    id: str
    name: str
    network: str
    last4: str
    status: Literal["active", "frozen", "reported_stolen"]
    linked_account_id: str


@dataclass
class Customer:
    """Represents a banking customer profile."""
    id: str
    full_name: str
    email: str
    tier: str
