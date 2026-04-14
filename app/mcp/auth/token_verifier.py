from __future__ import annotations

from app.config import settings

from fastmcp.server.auth import AccessToken
from fastmcp.server.auth.providers.jwt import JWTVerifier


class TokenVerifier(JWTVerifier):
    """Project-local JWT verifier configured from shared settings."""

    def __init__(
        self,
        *,
        jwks_uri: str | None = None,
        issuer: str | list[str] | None = None,
        audience: str | list[str] | None = None,
        algorithm: str = "RS256",
        required_scopes: list[str] | None = None,
        base_url: str | None = None,
    ) -> None:
        if not settings.idcs_domain:
            raise ValueError("IDCS_DOMAIN must be configured for TokenVerifier to function")

        resolved_jwks_uri = jwks_uri or f"https://{settings.idcs_domain}/admin/v1/SigningCert/jwk"
        resolved_issuer = issuer or "https://identity.oraclecloud.com/"
        resolved_audience = audience or f"https://{settings.idcs_domain}:443"

        super().__init__(
            jwks_uri=resolved_jwks_uri,
            issuer=resolved_issuer,
            audience=resolved_audience,
            algorithm=algorithm,
            required_scopes=required_scopes,
            base_url=base_url,
        )

    async def verify(self, token: str) -> AccessToken | None:
        """Small convenience wrapper for callers that prefer `verify()`."""
        return await self.verify_token(token)
