"""Agent definitions and runtime helpers for the banking assistant.

This module configures the OpenAI Agents SDK against OCI's OpenAI-compatible
endpoint, defines the specialist banking agents, and exposes the main helper
used by the FastAPI application to run agent conversations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from openai import APIConnectionError
from openai import APITimeoutError
from openai import AsyncOpenAI
from openai import InternalServerError
from agents import (
    Agent,
    Runner,
    SQLiteSession,
    set_default_openai_client,
    set_tracing_disabled,
)
from agents.mcp import MCPServer

from app.config import settings
from app.tools import (
    get_account_details,
    get_customer_overview,
    get_recent_transactions,
    list_accounts,
    list_cards,
    report_card_issue,
    transfer_between_accounts,
)

logger = logging.getLogger(__name__)
settings.runtime_dir.mkdir(parents=True, exist_ok=True)
CONVERSATIONS_DB_PATH = settings.runtime_dir / "conversations.db"


def configure_model_client() -> None:
    """Configure the Agents SDK for the OCI OpenAI-compatible endpoint."""
    if not settings.oci_base_url or not settings.oci_api_key or not settings.oci_project:
        raise ValueError(
            "Missing required OCI configuration. Set OCI_BASE_URL, OCI_GENAI_API_KEY, and OCI_GENAI_PROJECT_ID in .env."
        )

    client = AsyncOpenAI(
        base_url=settings.oci_base_url,
        api_key=settings.oci_api_key,
        project=settings.oci_project,
        max_retries=4,
        timeout=120.0,
    )
    set_default_openai_client(client, use_for_tracing=False)
    set_tracing_disabled(True)
    logger.info("Configured Agents SDK with OCI Responses API model=%s", settings.model)


configure_model_client()


COMMON_STYLE = (
    "You are a careful, friendly banking assistant for a demo application. "
    "Use tools whenever the user asks for account facts, balances, card status, transfers, or transactions. "
    "Do not invent balances, cards, or actions. "
    "For any request involving balances, transactions, cards, or transfers, call at least one tool before answering. "
    "When you have tool data, include the exact account name, account ID, card last4, and dollar amounts that matter. "
    "Never mention internal specialists, routing, handoffs, or that you are connecting the user to another agent. "
    "Respond as one unified banking assistant. "
    "Mention that this is a demo app when the user asks about security, regulations, or live banking operations."
)


accounts_agent = Agent(
    name="Accounts Specialist",
    model=settings.model,
    instructions=(
        f"{COMMON_STYLE} "
        "Handle account overviews, balances, recent transactions, and product questions. "
        "Prefer get_customer_overview for summaries, list_accounts for lists, "
        "get_account_details for single-account lookups, and get_recent_transactions for activity. "
        "When you answer, present account data in short bullets or short paragraphs with numbers included. "
        "For a request like 'show my balances', return the balances immediately instead of asking permission or describing what you will do."
    ),
    tools=[get_customer_overview, list_accounts, get_account_details, get_recent_transactions],
)


cards_agent = Agent(
    name="Cards Specialist",
    model=settings.model,
    instructions=(
        f"{COMMON_STYLE} "
        "Handle debit and credit card questions, card status, and suspicious-card reports. "
        "Use list_cards first when the user is unsure which card they mean. "
        "Always mention the card name, last4, and resulting status. "
        "If the user asks what cards they have, list them directly."
    ),
    tools=[list_cards, report_card_issue],
)


payments_agent = Agent(
    name="Payments Specialist",
    model=settings.model,
    instructions=(
        f"{COMMON_STYLE} "
        "Handle transfers and payment-related tasks. "
        "Before using transfer_between_accounts, make sure the user gave an exact from_account_id, to_account_id, and amount. "
        "If IDs are missing, ask a concise follow-up question and suggest calling list_accounts. "
        "After a successful transfer, mention the updated balances returned by the tool. "
        "When you ask follow-up questions, keep them short and specific."
    ),
    tools=[list_accounts, transfer_between_accounts, get_account_details],
)


triage_agent = Agent(
    name="Banking Concierge",
    model=settings.model,
    instructions=(
        f"{COMMON_STYLE} "
        "You are the main customer-facing banking assistant. "
        "Answer most requests yourself by using tools directly. "
        "Use get_customer_overview and list_accounts for balance questions, "
        "get_recent_transactions for activity questions, list_cards for card questions, "
        "and transfer_between_accounts only when the user supplied exact account IDs and amount. "
        "If needed, you may hand off internally to the specialist agents, but never say that to the user. "
        "Keep answers concise and action-oriented. "
        "If a user asks about their money or account activity, do not answer from general knowledge: use tools and return the actual data."
    ),
    tools=[
        get_customer_overview,
        list_accounts,
        get_account_details,
        get_recent_transactions,
        list_cards,
        report_card_issue,
        transfer_between_accounts,
    ],
    handoffs=[accounts_agent, cards_agent, payments_agent],
)


def build_runtime_agent(mcp_servers: list[MCPServer] | None = None) -> Agent[Any]:
    """Return the runtime agent, optionally enriched with MCP server access."""
    if not mcp_servers:
        return triage_agent

    mcp_guidance = (
        "An Oracle Database is available through SQLcl MCP tools and should be treated as the source of truth "
        "for customer, account, card, and transaction data. "
        f"Start by using the SQLcl MCP tools to connect to the saved SQLcl connection named '{settings.sqlcl_connection_name}'. "
        "Use read-only SQL for balance, card, and transaction lookups. "
        "Prefer querying the tables BANK_CUSTOMERS, BANK_ACCOUNTS, BANK_CARDS, and BANK_TRANSACTIONS. "
        "OCI Object Storage MCP tools are also available for statement and document storage. "
        "When the user asks to create, store, or list statements or communications, you may generate concise statement content and use the object storage tools to upload or inspect stored objects. "
        "Use the Python transfer and card-issue tools only for demo actions that update the in-memory workflow. "
        "Do not mention MCP, SQLcl, or internal storage tooling to the user."
    )

    return Agent(
        name=triage_agent.name,
        model=triage_agent.model,
        instructions=f"{triage_agent.instructions} {mcp_guidance}",
        tools=triage_agent.tools,
        mcp_servers=mcp_servers,
        handoffs=triage_agent.handoffs,
    )


def build_session(conversation_id: str) -> SQLiteSession:
    """Create or reopen the persisted conversation session for one chat thread."""
    return SQLiteSession(conversation_id, str(CONVERSATIONS_DB_PATH))


def _is_retryable_model_error(exc: Exception) -> bool:
    """Return ``True`` when the OCI model failure is safe to retry."""
    return isinstance(exc, (InternalServerError, APIConnectionError, APITimeoutError))


async def run_banking_agent(
    conversation_id: str,
    message: str,
    mcp_servers: list[MCPServer] | None = None,
) -> str:
    """Run one banking-agent turn with retries for transient OCI model failures."""
    session = build_session(conversation_id)
    runtime_agent = build_runtime_agent(mcp_servers)
    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            result = await Runner.run(runtime_agent, message, session=session)
            return str(result.final_output)
        except Exception as exc:
            last_error = exc
            if attempt == 3 or not _is_retryable_model_error(exc):
                raise
            delay_seconds = float(attempt)
            logger.warning(
                "Transient OCI model failure during chat run; retrying attempt %s/3 in %.1fs: %s",
                attempt + 1,
                delay_seconds,
                type(exc).__name__,
            )
            await asyncio.sleep(delay_seconds)

    if last_error is not None:
        raise last_error
    raise RuntimeError("The banking agent did not produce a response.")
