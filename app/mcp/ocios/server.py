from __future__ import annotations

"""FastMCP server for OCI Object Storage access over authenticated HTTP transport."""

import sys

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.config import settings
from app.mcp.ocios.registry import register_resources, register_tools


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)

def _build_auth_provider() -> JWTVerifier:
    if not settings.idcs_domain:
        raise ValueError("IDCS_DOMAIN or OIDC_DISCOVERY_URL is required for OCI Object Storage MCP auth.")

    return JWTVerifier(
        jwks_uri=f"https://{settings.idcs_domain}/admin/v1/SigningCert/jwk",
        issuer="https://identity.oraclecloud.com/",
        audience=f"https://{settings.idcs_domain}:443",
        algorithm="RS256",
    )


async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


def create_mcp_server() -> FastMCP:
    """Create the authenticated FastMCP server for OCI Object Storage tools."""
    mcp = FastMCP("Oracle Object Storage MCP Server", auth=_build_auth_provider())
    register_tools(mcp)
    register_resources(mcp)
    mcp.custom_route("/health", methods=["GET"])(health_check)
    return mcp


mcp = create_mcp_server()


def main() -> None:
    log("=" * 60)
    log("Starting Oracle Object Storage MCP Server")
    log("Transport: streamable-http")
    log(f"Host: {settings.ocios_mcp_host}")
    log(f"Port: {settings.ocios_mcp_port}")
    log("Tools registered: object storage namespace, upload, list, delete")
    log("=" * 60)
    mcp.run("streamable-http", host=settings.ocios_mcp_host, port=settings.ocios_mcp_port)


if __name__ == "__main__":
    main()
