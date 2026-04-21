"""Agent definitions and runtime helpers for the banking assistant.

This module configures the OpenAI Agents SDK against OCI's OpenAI-compatible
endpoint, defines the specialist banking agents, and exposes the main helper
used by the FastAPI application to run agent conversations.
"""

from __future__ import annotations

import asyncio
import ast
from json import JSONDecodeError
import json
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
from app.tools.manager import (
    list_all_customers,
    get_most_active_accounts,
    get_dormant_accounts,
    get_premium_customers,
    get_analytics_summary,
)
from app.tools import (
    fetch_accounts_view,
    fetch_bootstrap_view,
    fetch_cards_view,
    fetch_recent_activity_view,
    get_account_details,
    get_customer_overview,
    get_recent_transactions,
    list_accounts,
    list_cards,
    report_card_issue,
    transfer_between_accounts,
)

logger = logging.getLogger(__name__)
CONVERSATIONS_DB_PATH = settings.runtime_dir / "conversations.db"

_model_client_configured = False


def configure_model_client() -> None:
    """Configure the Agents SDK for the OCI OpenAI-compatible endpoint."""
    global _model_client_configured
    if _model_client_configured:
        return
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
    _model_client_configured = True
    logger.info("Configured Agents SDK with OCI Responses API model=%s", settings.model)


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
        "TRANSFER SAFETY RULE: Before calling transfer_between_accounts you MUST (1) confirm exact from_account_id, to_account_id, and amount with the user, "
        "(2) present a summary ('Transfer $X from Account A to Account B — shall I proceed?'), and "
        "(3) only call the tool after the user explicitly replies with 'yes', 'confirm', 'proceed', or equivalent affirmative language in their next message. "
        "Never call transfer_between_accounts based solely on the initial request, no matter how specific. "
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


bootstrap_view_agent = Agent(
    name="Bootstrap View Agent",
    model=settings.model,
    instructions=(
        "You prepare the authenticated user's home-page bootstrap payload. "
        "Always call fetch_bootstrap_view exactly once and stop. "
        "Do not add commentary or markdown."
    ),
    tools=[fetch_bootstrap_view],
    tool_use_behavior="stop_on_first_tool",
)


accounts_view_agent = Agent(
    name="Accounts View Agent",
    model=settings.model,
    instructions=(
        "You prepare the authenticated user's accounts API response. "
        "Always call fetch_accounts_view exactly once and stop. "
        "Do not add commentary or markdown."
    ),
    tools=[fetch_accounts_view],
    tool_use_behavior="stop_on_first_tool",
)


cards_view_agent = Agent(
    name="Cards View Agent",
    model=settings.model,
    instructions=(
        "You prepare the authenticated user's cards API response. "
        "Always call fetch_cards_view exactly once and stop. "
        "Do not add commentary or markdown."
    ),
    tools=[fetch_cards_view],
    tool_use_behavior="stop_on_first_tool",
)


activity_view_agent = Agent(
    name="Activity View Agent",
    model=settings.model,
    instructions=(
        "You prepare the authenticated user's recent activity API response. "
        "Always call fetch_recent_activity_view exactly once and stop. "
        "Do not add commentary or markdown."
    ),
    tools=[fetch_recent_activity_view],
    tool_use_behavior="stop_on_first_tool",
)


manager_agent = Agent(
    name="Bank Manager Assistant",
    model=settings.model,
    instructions=(
        "You are an analytics assistant exclusively for bank managers. "
        "Use tools to answer questions about all customers, active accounts, dormant accounts, premium customers, and aggregate KPIs. "
        "Always call a tool before answering — never invent numbers. "
        "Present data in clear tables or bullet lists. "
        "Do not discuss or reveal individual customer personal data beyond what is directly needed for manager reporting. "
        "Do not assist with end-customer transactions, transfers, or card actions."
    ),
    tools=[
        get_analytics_summary,
        list_all_customers,
        get_most_active_accounts,
        get_dormant_accounts,
        get_premium_customers,
    ],
)


def build_runtime_agent(mcp_servers: list[MCPServer] | None = None) -> Agent[Any]:
    """Return the runtime agent, optionally enriched with MCP server access."""
    if not mcp_servers:
        logger.debug("Building runtime agent without MCP servers.")
        return triage_agent

    mcp_guidance = (
        "An Oracle Database is available through SQLcl MCP tools and should be treated as the source of truth "
        "for customer, account, card, and transaction data. "
        f"Start by using the SQLcl MCP tools to connect to the saved SQLcl connection named '{settings.sqlcl_connection_name}'. "
        "CRITICAL SQL RULE: Only use read-only SELECT statements through the SQLcl MCP tools. "
        "Never issue INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or any other data-modification statement via SQLcl MCP. "
        "Prefer querying the tables BANK_CUSTOMERS, BANK_ACCOUNTS, BANK_CARDS, and BANK_TRANSACTIONS. "
        "OCI Object Storage MCP tools are also available for statement and document storage. "
        "When the user asks to create, store, or list statements or communications, you may generate concise statement content and use the object storage tools to upload or inspect stored objects. "
        "Use the Python transfer and card-issue tools only for demo actions that update the in-memory workflow. "
        "Do not mention MCP, SQLcl, or internal storage tooling to the user."
    )

    logger.info("Building runtime agent with %s MCP server(s).", len(mcp_servers))
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


def _serialize_agent_output(payload: Any) -> dict[str, Any]:
    """Convert endpoint-agent output into a JSON-serializable dictionary."""
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            decoded = json.loads(payload)
        except JSONDecodeError as exc:
            try:
                decoded = ast.literal_eval(payload)
            except (ValueError, SyntaxError) as literal_exc:
                raise ValueError(f"Expected JSON object from agent output, got: {payload}") from literal_exc
        if isinstance(decoded, dict):
            return decoded
    raise ValueError(f"Unsupported agent output type: {type(payload).__name__}")


async def _run_ui_agent(agent: Agent[Any], prompt: str) -> dict[str, Any]:
    """Run a UI endpoint agent and return its structured payload."""
    result = await Runner.run(agent, prompt, max_turns=3)
    return _serialize_agent_output(result.final_output)


def _is_retryable_model_error(exc: Exception) -> bool:
    """Return ``True`` when the OCI model failure is safe to retry."""
    return isinstance(exc, (InternalServerError, APIConnectionError, APITimeoutError))


_AGENT_TIMEOUT_SECONDS = 180.0


async def run_banking_agent(
    conversation_id: str,
    message: str,
    mcp_servers: list[MCPServer] | None = None,
) -> str:
    """Run one banking-agent turn with retries for transient OCI model failures."""
    session = build_session(conversation_id)
    runtime_agent = build_runtime_agent(mcp_servers)
    last_error: Exception | None = None
    logger.info(
        "Starting banking agent run conversation_id=%s message_chars=%s mcp_servers=%s",
        conversation_id,
        len(message),
        len(mcp_servers or []),
    )

    for attempt in range(1, 4):
        try:
            result = await asyncio.wait_for(
                Runner.run(runtime_agent, message, session=session),
                timeout=_AGENT_TIMEOUT_SECONDS,
            )
            logger.info("Banking agent run succeeded conversation_id=%s attempt=%s", conversation_id, attempt)
            return str(result.final_output)
        except asyncio.TimeoutError:
            logger.warning(
                "Banking agent run timed out after %.0fs conversation_id=%s attempt=%s",
                _AGENT_TIMEOUT_SECONDS,
                conversation_id,
                attempt,
            )
            raise TimeoutError(
                f"The agent did not respond within {int(_AGENT_TIMEOUT_SECONDS)} seconds. Please try again."
            )
        except Exception as exc:
            last_error = exc
            if attempt == 3 or not _is_retryable_model_error(exc):
                logger.info(
                    "Banking agent run failed conversation_id=%s attempt=%s error=%s",
                    conversation_id,
                    attempt,
                    type(exc).__name__,
                )
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


async def run_bootstrap_view_agent() -> dict[str, Any]:
    """Run the bootstrap-view agent and return the structured payload."""
    logger.info("Running bootstrap view agent.")
    return await _run_ui_agent(
        bootstrap_view_agent,
        "Load the authenticated customer's bootstrap payload for the home page.",
    )


async def run_accounts_view_agent() -> dict[str, Any]:
    """Run the accounts-view agent and return the structured payload."""
    logger.info("Running accounts view agent.")
    return await _run_ui_agent(
        accounts_view_agent,
        "Load the authenticated customer's accounts API payload.",
    )


async def run_cards_view_agent() -> dict[str, Any]:
    """Run the cards-view agent and return the structured payload."""
    logger.info("Running cards view agent.")
    return await _run_ui_agent(
        cards_view_agent,
        "Load the authenticated customer's cards API payload.",
    )


async def run_activity_view_agent() -> dict[str, Any]:
    """Run the activity-view agent and return the structured payload."""
    logger.info("Running activity view agent.")
    return await _run_ui_agent(
        activity_view_agent,
        "Load the authenticated customer's recent activity API payload.",
    )


async def run_manager_agent(conversation_id: str, message: str) -> str:
    """Run one manager-agent turn with retries for transient OCI model failures."""
    session = build_session(conversation_id)
    last_error: Exception | None = None
    logger.info(
        "Starting manager agent run conversation_id=%s message_chars=%s",
        conversation_id,
        len(message),
    )

    for attempt in range(1, 4):
        try:
            result = await asyncio.wait_for(
                Runner.run(manager_agent, message, session=session),
                timeout=_AGENT_TIMEOUT_SECONDS,
            )
            logger.info("Manager agent run succeeded conversation_id=%s attempt=%s", conversation_id, attempt)
            return str(result.final_output)
        except asyncio.TimeoutError:
            logger.warning(
                "Manager agent run timed out after %.0fs conversation_id=%s attempt=%s",
                _AGENT_TIMEOUT_SECONDS,
                conversation_id,
                attempt,
            )
            raise TimeoutError(
                f"The agent did not respond within {int(_AGENT_TIMEOUT_SECONDS)} seconds. Please try again."
            )
        except Exception as exc:
            last_error = exc
            if attempt == 3 or not _is_retryable_model_error(exc):
                logger.info(
                    "Manager agent run failed conversation_id=%s attempt=%s error=%s",
                    conversation_id,
                    attempt,
                    type(exc).__name__,
                )
                raise
            delay_seconds = float(attempt)
            logger.warning(
                "Transient OCI model failure during manager run; retrying attempt %s/3 in %.1fs: %s",
                attempt + 1,
                delay_seconds,
                type(exc).__name__,
            )
            await asyncio.sleep(delay_seconds)

    if last_error is not None:
        raise last_error
    raise RuntimeError("The manager agent did not produce a response.")
