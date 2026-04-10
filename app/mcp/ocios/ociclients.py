import oci
from oci.auth.signers import TokenExchangeSigner
from oci.object_storage import ObjectStorageClient

from app.config import settings


_object_storage_clients: dict[str, ObjectStorageClient] = {}
_signers_by_token_id: dict[str, TokenExchangeSigner] = {}


def _build_oci_config(region: str | None = None) -> dict:
    resolved_region = (region or "").strip()
    if not resolved_region:
        raise ValueError("OCI region is required for the Object Storage MCP server.")
    return {"region": resolved_region}


def _get_oci_domain_id() -> str:
    if not settings.idcs_domain:
        raise ValueError("IDCS_DOMAIN or OIDC_DISCOVERY_URL is required for OCI token exchange.")

    domain = settings.idcs_domain.strip()
    domain = domain.removeprefix("https://")
    domain = domain.split("/", 1)[0]
    return domain.split(".", 1)[0]


def get_oci_signer(mcp_token) -> TokenExchangeSigner:
    token_id = (getattr(mcp_token, "claims", None) or {}).get("jti") or getattr(mcp_token, "token", None)
    if not token_id:
        raise ValueError("Authenticated OCI Object Storage calls require a bearer token with a token identifier.")

    cached_signer = _signers_by_token_id.get(token_id)
    if cached_signer is not None:
        return cached_signer

    signer = TokenExchangeSigner(
        oci_domain_url=_get_oci_domain_id(),
        jwt_or_func=mcp_token.token,
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
    )
    _signers_by_token_id[token_id] = signer
    return signer


def get_os_client(mcp_token, region: str) -> ObjectStorageClient:
    """Return a cached Object Storage client for the requested OCI region and token."""
    resolved_region = region or ""
    if not resolved_region:
        raise ValueError("A region must be provided to Object Storage tools.")

    token_id = (getattr(mcp_token, "claims", None) or {}).get("jti") or "default"
    cache_key = f"{resolved_region}:{token_id}"
    if cache_key not in _object_storage_clients:
        config = _build_oci_config(region=resolved_region)
        _object_storage_clients[cache_key] = ObjectStorageClient(
            config=config,
            signer=get_oci_signer(mcp_token),
        )
    return _object_storage_clients[cache_key]
