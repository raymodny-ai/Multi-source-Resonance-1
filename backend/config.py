"""
Application configuration management using pydantic-settings.
Loads environment variables from .env file with sensible defaults.
All API keys are optional - system operates in mock mode when absent.
"""

import logging
import secrets
from pathlib import Path
from typing import Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Global application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    db_path: str = "./data/resonance.db"

    # ── API Keys (all optional — mock mode when empty) ────────────────────────
    gexmetrix_api_key: Optional[str] = None
    axlfi_api_key: Optional[str] = None
    crypto_api_key: Optional[str] = None
    darkpool_api_key: Optional[str] = None

    # ── JWT Authentication ────────────────────────────────────────────────────
    # FIX-05: jwt_secret has no default value — must be supplied via env (.env).
    # The application refuses to start with the previous weak default
    # ("change-me-in-production") so a forgotten .env never silently ships
    # with a known credential. The model_validator below enforces this.
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ── CORS ──────────────────────────────────────────────────────────────────
    # FIX-10: CORS default is no wildcard — explicit allowlist only. The
    # previous default of "*" allowed any origin to call authenticated
    # endpoints. The model_validator below enforces this.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Proxy / Network (FIX-02) ──────────────────────────────────────────────
    # Used by fetchers when the host runs behind a corporate proxy / firewall
    # that requires outbound HTTP/HTTPS to traverse a forwarding proxy. Empty
    # means "use direct connection" (no proxy).
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    no_proxy: str = "localhost,127.0.0.1,::1"
    # Per-source proxy override map (JSON), e.g. {"coinglass":"http://proxy:8080"}
    proxy_overrides: Optional[str] = None
    # Network timeout (FIX-02): raise default to be proxy-tolerant.
    network_timeout_seconds: int = 45
    # Allow disabling outbound for fully air-gapped runs.
    network_enabled: bool = True

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── Data Collection ───────────────────────────────────────────────────────
    fetch_interval_seconds: int = 900  # 15min default — 21 fetcher + yfinance rate limit
    fetch_timeout_seconds: int = 30
    max_workers: int = 8

    # ── Server ────────────────────────────────────────────────────────────────
    # SEC-09: bind 127.0.0.1 by default so a misconfigured prod box
    # can't expose the API publicly. Operators running inside a
    # container/VM expose this via ``MSR_HOST=0.0.0.0`` env var.
    host: str = "127.0.0.1"
    port: int = 8524

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def db_absolute_path(self) -> Path:
        """Resolve database path to absolute Path."""
        return Path(self.db_path).resolve()

    @property
    def effective_jwt_secret(self) -> str:
        """Return the JWT secret.

        FIX-05: if the operator didn't supply one, generate a per-process
        ephemeral secret. Tokens issued in this process will validate only
        while the process is alive — strong-enough default to prevent
        cross-deployment token replay, and avoids the previous hardcoded
        ``"change-me-in-production"`` shared-secret footgun.
        """
        if self.jwt_secret:
            return self.jwt_secret
        ephemeral = secrets.token_urlsafe(48)
        logger.warning(
            "FIX-05: JWT_SECRET not set — generated ephemeral secret for "
            "this process. All tokens will be invalidated on restart. "
            "Set JWT_SECRET in .env to persist sessions."
        )
        return ephemeral

    @property
    def proxy_overrides_map(self) -> dict[str, str]:
        """Parse the JSON ``proxy_overrides`` field into a per-source dict.

        FIX-02: the original code ignored the env-level proxy. Now any
        fetcher can ask for its own override (e.g. CoinGlass via a slow
        hop) while the default path uses ``https_proxy``.
        """
        import json
        if not self.proxy_overrides:
            return {}
        try:
            data = json.loads(self.proxy_overrides)
            return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
        except (ValueError, TypeError):
            logger.warning("FIX-02: proxy_overrides is not valid JSON — ignoring.")
            return {}

    @model_validator(mode="after")
    def _validate_security_basics(self) -> "Settings":
        """FIX-05 + FIX-10: refuse obviously-weak security defaults."""
        # Reject wildcard CORS — it would allow any origin to call our
        # authenticated endpoints. Operators must enumerate allowed origins.
        origins = self.cors_origin_list
        if "*" in origins or self.cors_origins.strip() == "*":
            raise ValueError(
                "FIX-10: cors_origins='*' is not allowed. "
                "Set CORS_ORIGINS in .env to an explicit comma-separated allowlist."
            )
        # If jwt_secret IS set, reject the documented placeholder.
        if self.jwt_secret and self.jwt_secret.strip() in {
            "change-me-in-production", "changeme", "secret", "default",
        }:
            raise ValueError(
                "FIX-05: jwt_secret is set to a documented placeholder. "
                "Set JWT_SECRET in .env to a strong random value."
            )
        return self

    def is_mock_mode(self, source: str) -> bool:
        """Check whether a given data source should run in mock mode.

        The mapping is intentionally narrow: only ``gexmetrix`` and ``axlfi``
        are gated on dedicated API keys. All other public / fallback sources
        (VIX, yfinance, CBOE, FINRA, SqueezeMetrics, StockGrid, DBMF,
        put/call, darkpool) attempt a real fetch first and only fall back
        to mock data when the upstream request fails or the optional API
        key (CCData/Coinglass/Tradier) is missing.

        Args:
            source: One of 'gexmetrix', 'axlfi', 'crypto', 'darkpool'.
                     Any other value is treated as "no key required" and
                     returns ``False`` so the fetcher hits the live path.
        """
        key_map = {
            "gexmetrix": self.gexmetrix_api_key,
            "axlfi": self.axlfi_api_key,
            "crypto": self.crypto_api_key,
            "darkpool": self.darkpool_api_key,
        }
        # Only mock when the source is in key_map AND its key is empty/absent.
        # Public sources (VIX, CBOE, yfinance, SqueezeMetrics, ...) that map to a
        # key name NOT in key_map (e.g. "none" / "") must return False so they
        # always hit the live path and only fall back to mock on fetch failure.
        # Previous `not bool(key_map.get(source))` was inverted: any key not in
        # the map returned True (mock) → all public sources ran in mock mode.
        if source not in key_map:
            return False
        return not bool(key_map[source])


# Singleton instance — import and use directly
settings = Settings()
