"""FastAPI entrypoint for the agentic banking demo application.

This module wires together authentication, the banking agent, Oracle-backed
data access, statement storage, and the static frontend experience.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask
from starlette.middleware.sessions import SessionMiddleware
from agents.mcp import MCPServerManager

from app.agents import run_banking_agent
from app.auth import (
    MismatchingStateError,
    clear_access_token,
    clear_oidc_state,
    get_access_token,
    get_current_user,
    maybe_user,
    oauth,
    store_access_token,
)
from app.config import settings
from app.data import BankingDataUnavailableError, CustomerNotLinkedError, data_store, statement_store
from app.mcp import build_mcp_manager, build_ocios_server
from app.user_context import authenticated_user_scope


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
LOGO_PATH = BASE_DIR / "logo.png"
DATA_DIR.mkdir(exist_ok=True)
logger = logging.getLogger(__name__)


def _user_log_context(user: dict | None) -> str:
    """Return a compact log label for the current authenticated user."""
    if not user:
        return "anonymous"
    return f"sub={user.get('sub')} email={user.get('email')}"


def _message_needs_statement_mcp(message: str) -> bool:
    """Return ``True`` when a chat request likely needs statement storage tools."""
    normalized = message.strip().lower()
    if not normalized:
        return False
    keywords = {
        "statement",
        "statements",
        "document",
        "documents",
        "tax",
        "communication",
        "communications",
        "object storage",
        "file",
        "files",
        "pdf",
        "upload",
        "download",
    }
    return any(keyword in normalized for keyword in keywords)


def _format_money(amount: float) -> str:
    """Format a numeric amount as display-ready US currency text."""
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def _format_fast_accounts_reply(accounts: list[dict]) -> str:
    lines = ["Here are your current account balances:"]
    for account in accounts:
        lines.append(
            f"- {account['name']} ({account['id']}): {_format_money(float(account['balance']))} {account.get('currency', 'USD')}"
        )
    return "\n".join(lines)


def _format_fast_cards_reply(cards: list[dict]) -> str:
    lines = ["Here are your linked cards:"]
    for card in cards:
        lines.append(
            f"- {card['name']} ({card['id']}): {card['network']} ending in {card['last4']}, status {card['status']}"
        )
    return "\n".join(lines)


def _format_fast_transactions_reply(account_label: str, transactions: list[dict]) -> str:
    lines = [f"Here are the most recent transactions for {account_label}:"]
    for item in transactions:
        lines.append(
            f"- {item['posted_on']}: {item['description']} ({item['category']}) {_format_money(float(item['amount']))}"
        )
    return "\n".join(lines)


async def _try_fast_chat_reply(message: str, user: dict) -> str | None:
    """Handle simple balance, card, and transaction requests without agent runs."""
    normalized = message.strip().lower()
    identity_subject = user.get("sub")
    email = user.get("email")
    logger.debug("Evaluating fast chat path for %s", _user_log_context(user))

    if any(phrase in normalized for phrase in {"show me all my account balances", "show me my balances", "show my balances", "account balances", "all my account balances"}):
        logger.info("Fast chat matched account balance request for %s", _user_log_context(user))
        accounts = await data_store.list_accounts(identity_subject=identity_subject, email=email)
        if not accounts:
            return "No accounts were found for the logged-in user."
        return _format_fast_accounts_reply(accounts)

    if any(phrase in normalized for phrase in {"what cards do i have", "show my cards", "list my cards", "what are my cards", "cards on my account"}):
        logger.info("Fast chat matched card list request for %s", _user_log_context(user))
        cards = await data_store.list_cards(identity_subject=identity_subject, email=email)
        if not cards:
            return "No cards were found for the logged-in user."
        return _format_fast_cards_reply(cards)

    if "recent" in normalized and "transaction" in normalized:
        account_lookup = "checking"
        if "savings" in normalized:
            account_lookup = "savings"
        elif "credit" in normalized or "card" in normalized:
            account_lookup = "credit"
        logger.info(
            "Fast chat matched recent transactions request for %s account_lookup=%s",
            _user_log_context(user),
            account_lookup,
        )
        transactions = await data_store.recent_transactions(
            account_lookup,
            limit=5,
            identity_subject=identity_subject,
            email=email,
        )
        if not transactions:
            return f"No recent transactions were found for {account_lookup}."
        return _format_fast_transactions_reply(account_lookup, transactions)

    logger.debug("Fast chat path did not match any shortcut for %s", _user_log_context(user))
    return None


def _bootstrap_unavailable_response(user: dict, message: str) -> dict:
    """Build the bootstrap payload returned during banking-data outages."""
    return {
        "app_name": settings.app_name,
        "user": user,
        "data_source": "oracle_sqlcl",
        "customer_summary": None,
        "data_unavailable": True,
        "message": message,
        "suggested_prompts": [],
    }


def _bootstrap_unlinked_response(user: dict, message: str) -> dict:
    """Build the bootstrap payload returned when no customer link exists."""
    return {
        "app_name": settings.app_name,
        "user": user,
        "data_source": "oracle_sqlcl",
        "customer_summary": None,
        "no_matching_account": True,
        "message": message,
        "suggested_prompts": [],
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage shared MCP resources during FastAPI startup and shutdown."""
    logger.info("Starting FastAPI application lifespan.")
    manager = build_mcp_manager()
    if manager is not None:
        async with manager as connected_manager:
            app.state.mcp_manager = connected_manager
            await data_store.start(connected_manager)
            try:
                logger.info("Application startup completed with shared MCP manager.")
                yield
            finally:
                logger.info("Shutting down application resources.")
                await data_store.stop()
    else:
        app.state.mcp_manager = None
        await data_store.start(None)
        try:
            logger.info("Application startup completed without shared MCP manager.")
            yield
        finally:
            logger.info("Shutting down application resources.")
            await data_store.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, same_site="lax")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str


@app.get("/", response_model=None)
async def index(request: Request) -> FileResponse | RedirectResponse:
    if not maybe_user(request):
        logger.debug("Redirecting anonymous user from / to /login")
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/statements", response_model=None)
async def statements_page(request: Request) -> FileResponse | RedirectResponse:
    if not maybe_user(request):
        logger.debug("Redirecting anonymous user from /statements to /login")
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse(STATIC_DIR / "statements.html")


@app.get("/profile", response_model=None)
async def profile_page(request: Request) -> FileResponse | RedirectResponse:
    if not maybe_user(request):
        logger.debug("Redirecting anonymous user from /profile to /login")
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse(STATIC_DIR / "profile.html")


@app.get("/logo.png", response_model=None)
async def bank_logo() -> FileResponse:
    return FileResponse(LOGO_PATH)

@app.get("/login", response_model=None)
async def login_page(request: Request) -> FileResponse | RedirectResponse:
    if maybe_user(request):
        logger.debug("Redirecting authenticated user from /login to /")
        return RedirectResponse(url="/", status_code=302)
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/auth/login", response_model=None)
async def auth_login(request: Request):
    if maybe_user(request):
        logger.debug("Skipping auth/login because session is already authenticated.")
        return RedirectResponse(url="/", status_code=302)

    clear_oidc_state(request)
    redirect_uri = settings.oidc_redirect_uri
    logger.info("Starting OIDC login redirect redirect_uri=%s", redirect_uri)
    return await oauth.oci.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback", response_model=None)
async def auth_callback(request: Request) -> RedirectResponse:
    try:
        token = await oauth.oci.authorize_access_token(request)
    except MismatchingStateError:
        logger.info("OIDC callback failed due to mismatching state.")
        clear_access_token(request)
        clear_oidc_state(request)
        request.session.pop("user", None)
        return RedirectResponse(url="/login", status_code=302)

    clear_oidc_state(request)
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.oci.userinfo(token=token)

    request.session["user"] = {
        "sub": userinfo.get("sub"),
        "name": userinfo.get("name") or userinfo.get("preferred_username") or "Profile",
        "email": userinfo.get("email"),
        "preferred_username": userinfo.get("preferred_username"),
    }
    logger.info(
        "OIDC callback succeeded for sub=%s email=%s",
        userinfo.get("sub"),
        userinfo.get("email"),
    )
    store_access_token(request, token.get("access_token") or token.get("id_token"))
    return RedirectResponse(
        url="/",
        status_code=302,
        background=BackgroundTask(
            data_store.prewarm_customer_summary,
            identity_subject=userinfo.get("sub"),
            email=userinfo.get("email"),
        ),
    )


@app.get("/auth/logout", response_model=None)
async def auth_logout(request: Request) -> RedirectResponse:
    logger.info("Logging out session user=%s", _user_log_context(maybe_user(request)))
    clear_access_token(request)
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@app.get("/api/bootstrap")
async def bootstrap(user: dict = Depends(get_current_user)) -> dict:
    try:
        logger.info("Handling bootstrap request for %s", _user_log_context(user))
        identity_subject = user.get("sub")
        email = user.get("email")
        customer_summary = await data_store.get_customer_summary(
            identity_subject=identity_subject,
            email=email,
        )
        snapshot = customer_summary.get("snapshot", {})
        linked_accounts = int(snapshot.get("linked_accounts", 0) or 0)
        if linked_accounts == 0:
            return {
                "app_name": settings.app_name,
                "user": user,
                "data_source": "oracle_sqlcl",
                "customer_summary": None,
                "no_matching_account": True,
                "message": "No matching account found for the logged-in user.",
                "suggested_prompts": [],
            }
        return {
            "app_name": settings.app_name,
            "user": user,
            "data_source": "oracle_sqlcl",
            "customer_summary": customer_summary,
            "suggested_prompts": [
                "Show me all my account balances.",
                "What are my most recent checking transactions?",
                "Transfer $200 from CHK-001 to SAV-001 for my vacation fund.",
                "Freeze my debit card.",
            ],
        }
    except CustomerNotLinkedError as exc:
        logger.info("Bootstrap found no linked account for %s", _user_log_context(user))
        return _bootstrap_unlinked_response(user, str(exc))
    except BankingDataUnavailableError as exc:
        logger.info("Bootstrap found banking data unavailable for %s", _user_log_context(user))
        return _bootstrap_unavailable_response(user, str(exc))


@app.get("/api/accounts")
async def get_accounts(user: dict = Depends(get_current_user)) -> dict:
    try:
        logger.info("Handling accounts request for %s", _user_log_context(user))
        return {
            "accounts": await data_store.list_accounts(
                identity_subject=user.get("sub"),
                email=user.get("email"),
            )
        }
    except CustomerNotLinkedError as exc:
        logger.info("Accounts request found no linked account for %s", _user_log_context(user))
        return {"accounts": [], "message": str(exc)}
    except BankingDataUnavailableError as exc:
        logger.info("Accounts request found banking data unavailable for %s", _user_log_context(user))
        return {"accounts": [], "message": str(exc), "data_unavailable": True}


@app.get("/api/cards")
async def get_cards(user: dict = Depends(get_current_user)) -> dict:
    try:
        logger.info("Handling cards request for %s", _user_log_context(user))
        return {
            "cards": await data_store.list_cards(
                identity_subject=user.get("sub"),
                email=user.get("email"),
            )
        }
    except CustomerNotLinkedError as exc:
        logger.info("Cards request found no linked account for %s", _user_log_context(user))
        return {"cards": [], "message": str(exc)}
    except BankingDataUnavailableError as exc:
        logger.info("Cards request found banking data unavailable for %s", _user_log_context(user))
        return {"cards": [], "message": str(exc), "data_unavailable": True}


@app.get("/api/activity")
async def get_recent_activity(user: dict = Depends(get_current_user)) -> dict:
    try:
        logger.info("Handling recent activity request for %s", _user_log_context(user))
        return {
            "recent_activity": await data_store.recent_activity(
                identity_subject=user.get("sub"),
                email=user.get("email"),
            )
        }
    except CustomerNotLinkedError as exc:
        logger.info("Recent activity request found no linked account for %s", _user_log_context(user))
        return {"recent_activity": [], "message": str(exc)}
    except BankingDataUnavailableError as exc:
        logger.info("Recent activity request found banking data unavailable for %s", _user_log_context(user))
        return {"recent_activity": [], "message": str(exc), "data_unavailable": True}


@app.post("/api/statements/generate-demo")
async def generate_demo_statements(request: Request, user: dict = Depends(get_current_user)) -> dict:
    try:
        logger.info("Handling statement generation request for %s", _user_log_context(user))
        return await statement_store.generate_demo_documents(
            request,
            identity_subject=user.get("sub"),
            email=user.get("email"),
        )
    except CustomerNotLinkedError as exc:
        logger.info("Statement generation found no linked account for %s", _user_log_context(user))
        return {"success": False, "message": str(exc), "items": []}
    except BankingDataUnavailableError as exc:
        logger.info("Statement generation found banking data unavailable for %s", _user_log_context(user))
        return {"success": False, "message": str(exc), "items": [], "data_unavailable": True}
    except Exception as exc:
        logger.exception("Failed to generate demo statements")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/statements/{category}")
async def get_statements(category: str, request: Request, user: dict = Depends(get_current_user)) -> dict:
    try:
        logger.info("Handling statement list request category=%s for %s", category, _user_log_context(user))
        return await statement_store.list_documents(
            request,
            category=category,
            identity_subject=user.get("sub"),
            email=user.get("email"),
        )
    except CustomerNotLinkedError as exc:
        logger.info("Statement list found no linked account for %s", _user_log_context(user))
        return {"category": category, "items": [], "message": str(exc)}
    except BankingDataUnavailableError as exc:
        logger.info("Statement list found banking data unavailable for %s", _user_log_context(user))
        return {"category": category, "items": [], "message": str(exc), "data_unavailable": True}
    except Exception as exc:
        logger.exception("Failed to fetch statements for category %s", category)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/statements/{category}/content")
async def get_statement_content(
    category: str,
    object_name: str,
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    try:
        logger.info(
            "Handling statement content request category=%s object_name=%s for %s",
            category,
            object_name,
            _user_log_context(user),
        )
        return await statement_store.get_document(
            request,
            category=category,
            object_name=object_name,
            identity_subject=user.get("sub"),
            email=user.get("email"),
        )
    except CustomerNotLinkedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BankingDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to fetch statement content for %s", object_name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    payload: ChatRequest,
    _user: dict = Depends(get_current_user),
) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    conversation_id = payload.conversation_id or str(uuid4())
    try:
        logger.info(
            "Handling chat request conversation_id=%s for %s",
            conversation_id,
            _user_log_context(_user),
        )
        logger.debug("Chat request message=%s", message)
        fast_reply = await _try_fast_chat_reply(message, _user)
        if fast_reply is not None:
            logger.info("Returning fast chat reply conversation_id=%s", conversation_id)
            return ChatResponse(conversation_id=conversation_id, reply=fast_reply)

        if _message_needs_statement_mcp(message):
            logger.info("Chat request conversation_id=%s requires statement MCP access", conversation_id)
            ocios_server = build_ocios_server(get_access_token(request))
            if ocios_server is not None:
                async with MCPServerManager([ocios_server], strict=False) as ocios_manager:
                    active_servers = list(ocios_manager.active_servers)
                    logger.debug(
                        "Chat request conversation_id=%s using %s statement MCP server(s)",
                        conversation_id,
                        len(active_servers),
                    )
                    with authenticated_user_scope(_user):
                        reply = await run_banking_agent(
                            conversation_id,
                            message,
                            mcp_servers=active_servers or None,
                        )
            else:
                logger.info("Statement MCP was requested but no Object Storage server was available.")
                with authenticated_user_scope(_user):
                    reply = await run_banking_agent(
                        conversation_id,
                        message,
                        mcp_servers=None,
                    )
        else:
            logger.debug("Chat request conversation_id=%s using runtime agent without statement MCP", conversation_id)
            with authenticated_user_scope(_user):
                reply = await run_banking_agent(
                    conversation_id,
                    message,
                    mcp_servers=None,
                )
        logger.info("Completed chat request conversation_id=%s", conversation_id)
        return ChatResponse(conversation_id=conversation_id, reply=reply)
    except CustomerNotLinkedError as exc:
        logger.info("Chat request found no linked account for %s", _user_log_context(_user))
        return ChatResponse(conversation_id=conversation_id, reply=str(exc))
    except BankingDataUnavailableError as exc:
        logger.info("Chat request found banking data unavailable for %s", _user_log_context(_user))
        return ChatResponse(conversation_id=conversation_id, reply=str(exc))
    except Exception as exc:
        logger.exception("Chat request failed for conversation %s", conversation_id)
        return JSONResponse(
            status_code=500,
            content={
                "detail": (
                    "Agent request failed before the banking response was generated. "
                    f"{type(exc).__name__}: {exc}"
                )
            },
        )
