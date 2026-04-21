"""OCI SDK client helpers used by the Object Storage FastMCP server."""

import time

from oci.auth.signers import TokenExchangeSigner
from oci.object_storage import ObjectStorageClient

from app.config import settings

_CACHE_TTL_SECONDS = 3600.0

_object_storage_clients: dict[str, tuple[float, ObjectStorageClient]] = {}
_signers_by_token_id: dict[str, tuple[float, TokenExchangeSigner]] = {}


def _evict_expired() -> None:
    now = time.monotonic()
    expired_signers = [k for k, (exp, _) in _signers_by_token_id.items() if now >= exp]
    for k in expired_signers:
        del _signers_by_token_id[k]
    expired_clients = [k for k, (exp, _) in _object_storage_clients.items() if now >= exp]
    for k in expired_clients:
        del _object_storage_clients[k]


def _build_oci_config(region: str | None = None) -> dict:
    """Build the minimal OCI SDK config required for regional API clients."""
    resolved_region = (region or "").strip()
    if not resolved_region:
        raise ValueError("OCI region is required for the Object Storage MCP server.")
    return {"region": resolved_region}


def _get_oci_domain_id() -> str:
    """Extract the OCI Identity Domain identifier used for token exchange."""
    if not settings.idcs_domain:
        raise ValueError("IDCS_DOMAIN or OIDC_DISCOVERY_URL is required for OCI token exchange.")

    domain = settings.idcs_domain.strip()
    domain = domain.removeprefix("https://")
    domain = domain.split("/", 1)[0]
    return domain.split(".", 1)[0]


def get_oci_signer(mcp_token) -> TokenExchangeSigner:
    """Return a cached token-exchange signer for the current bearer token."""
    _evict_expired()
    token_id = (getattr(mcp_token, "claims", None) or {}).get("jti") or getattr(mcp_token, "token", None)
    if not token_id:
        raise ValueError("Authenticated OCI Object Storage calls require a bearer token with a token identifier.")

    cached = _signers_by_token_id.get(token_id)
    if cached is not None:
        return cached[1]

    signer = TokenExchangeSigner(
        oci_domain_url=_get_oci_domain_id(),
        jwt_or_func=mcp_token.token,
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
    )
    _signers_by_token_id[token_id] = (time.monotonic() + _CACHE_TTL_SECONDS, signer)
    return signer


def get_os_client(mcp_token, region: str) -> ObjectStorageClient:
    """Return a cached Object Storage client for the requested OCI region and token."""
    _evict_expired()
    resolved_region = region or ""
    if not resolved_region:
        raise ValueError("A region must be provided to Object Storage tools.")

    token_id = (getattr(mcp_token, "claims", None) or {}).get("jti") or "default"
    cache_key = f"{resolved_region}:{token_id}"
    cached = _object_storage_clients.get(cache_key)
    if cached is None:
        config = _build_oci_config(region=resolved_region)
        client = ObjectStorageClient(
            config=config,
            signer=get_oci_signer(mcp_token),
        )
        _object_storage_clients[cache_key] = (time.monotonic() + _CACHE_TTL_SECONDS, client)
        return client
    return cached[1]
