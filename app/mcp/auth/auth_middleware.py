from __future__ import annotations

from contextlib import suppress

from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.types import ErrorData
from starlette.authentication import AuthCredentials

from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import Middleware, MiddlewareContext

from .token_verifier import TokenVerifier

class OCITokenAuthMiddleware(Middleware):
    """FastMCP middleware that validates bearer tokens for MCP requests."""

    def __init__(self):
        self.token_verifier = TokenVerifier()

    async def on_request(self, context: MiddlewareContext, call_next):
        request = get_http_request()
        authorization = request.headers.get("authorization", "").strip()

        if not authorization:
            raise self._auth_error("Missing Authorization header")

        scheme, _, token = authorization.partition(" ")
        token = token.strip()
        if scheme.lower() != "bearer" or not token:
            raise self._auth_error("Invalid Authorization header")

        access_token = await self.token_verifier.verify(token)
        if access_token is None:
            raise self._auth_error("Invalid or expired bearer token")

        request.scope["auth"] = AuthCredentials(access_token.scopes)
        request.scope["user"] = AuthenticatedUser(access_token)

        auth_context_token = auth_context_var.set(request.scope["user"])
        try:
            if context.fastmcp_context is not None:
                context.fastmcp_context.set_state("access_token", access_token)
                context.fastmcp_context.set_state(
                    "token_claims", dict(access_token.claims or {})
                )
            return await call_next(context)
        finally:
            auth_context_var.reset(auth_context_token)
            with suppress(KeyError):
                del request.scope["auth"]
            with suppress(KeyError):
                del request.scope["user"]

    @staticmethod
    def _auth_error(message: str) -> McpError:
        return McpError(
            ErrorData(
                code=-32001,
                message=message,
                data={"auth_scheme": "Bearer"},
            )
        )
