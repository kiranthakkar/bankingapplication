from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass
class Transaction:
    id: str
    account_id: str
    posted_on: date
    description: str
    amount: float
    category: str


@dataclass
class Account:
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
    id: str
    name: str
    network: str
    last4: str
    status: Literal["active", "frozen", "reported_stolen"]
    linked_account_id: str


@dataclass
class Customer:
    id: str
    full_name: str
    email: str
    tier: str
