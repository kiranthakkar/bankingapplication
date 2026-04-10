from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)


def _clean_env_value(name: str) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    cleaned = raw.strip().strip('"').strip("'").strip()
    return cleaned or None


def _split_args(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part for part in raw.split() if part]


def _bool_env(name: str, default: bool = False) -> bool:
    raw = _clean_env_value(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _host_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    return parsed.netloc or None


@dataclass(frozen=True)
class Settings:
    app_name: str = "Agentic Banking Demo"
    model: str = _clean_env_value("OCI_MODEL") or "openai.gpt-oss-120b"
    oci_base_url: str | None = _clean_env_value("OCI_BASE_URL")
    oci_api_key: str | None = _clean_env_value("OCI_GENAI_API_KEY")
    oci_project: str | None = _clean_env_value("OCI_GENAI_PROJECT_ID")
    session_secret: str = _clean_env_value("SESSION_SECRET") or "dev-session-secret-change-me"
    oidc_discovery_url: str | None = _clean_env_value("OIDC_DISCOVERY_URL")
    oidc_client_id: str | None = _clean_env_value("OIDC_CLIENT_ID")
    oidc_client_secret: str | None = _clean_env_value("OIDC_CLIENT_SECRET")
    oidc_redirect_uri: str = _clean_env_value("OIDC_REDIRECT_URI") or "http://localhost:8000/auth/callback"
    oidc_scopes: str = _clean_env_value("OIDC_SCOPES") or "openid profile email"
    idcs_domain: str | None = _clean_env_value("IDCS_DOMAIN") or _host_from_url(
        _clean_env_value("OIDC_DISCOVERY_URL")
    )
    sqlcl_path: str | None = _clean_env_value("SQLCL_PATH")
    sqlcl_connection_name: str | None = _clean_env_value("SQLCL_CONNECTION_NAME")
    sqlcl_mcp_args: list[str] = field(
        default_factory=lambda: _split_args(_clean_env_value("SQLCL_MCP_ARGS") or "-mcp")
    )
    ocios_mcp_enabled: bool = _bool_env("OCIOS_MCP_ENABLED", default=False)
    ocios_mcp_host: str = _clean_env_value("OCIOS_MCP_HOST") or "127.0.0.1"
    ocios_mcp_port: int = int(_clean_env_value("OCIOS_MCP_PORT") or "9001")
    ocios_mcp_url: str = _clean_env_value("OCIOS_MCP_URL") or (
        f"http://{_clean_env_value('OCIOS_MCP_HOST') or '127.0.0.1'}:{int(_clean_env_value('OCIOS_MCP_PORT') or '9001')}/mcp"
    )
    statements_region: str | None = _clean_env_value("STATEMENTS_REGION")
    statements_bucket: str | None = _clean_env_value("STATEMENTS_BUCKET")
    runtime_dir: Path = Path(_clean_env_value("APP_RUNTIME_DIR") or (Path(tempfile.gettempdir()) / "agentic-banking-demo"))
    port: int = int(os.getenv("PORT", "8000"))

    @property
    def sqlcl_enabled(self) -> bool:
        return bool(self.sqlcl_path and self.sqlcl_connection_name)


settings = Settings()

logger.info(
    "Resolved OCI config: base_url=%s project_set=%s model=%s",
    settings.oci_base_url,
    bool(settings.oci_project),
    settings.model,
)
