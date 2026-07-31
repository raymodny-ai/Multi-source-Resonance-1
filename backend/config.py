"""
Application configuration management using pydantic-settings.
Loads environment variables from .env file with sensible defaults.
All API keys are optional - system operates in mock mode when absent.
"""

from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── Data Collection ───────────────────────────────────────────────────────
    fetch_interval_seconds: int = 900  # 15min default — 21 fetcher + yfinance rate limit
    fetch_timeout_seconds: int = 30
    max_workers: int = 8

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
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
        return not bool(key_map.get(source))


# Singleton instance — import and use directly
settings = Settings()
