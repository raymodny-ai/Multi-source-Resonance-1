"""
Temporary base fetcher class (base_alt.py).

This module provides a compatible base class for all data fetchers.
It will be replaced by base.py once the other agent creates it.
To migrate: change `from backend.fetchers.base_alt import BaseFetcher`
to `from backend.fetchers.base import BaseFetcher`.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from backend.config import settings


class BaseFetcher(ABC):
    """Abstract base class for all data fetchers.

    Provides:
    - Unified async fetch() interface
    - Automatic mock mode when API key is missing
    - HTTP client lifecycle management (httpx.AsyncClient)
    - Structured logging and error handling
    - Source status tracking
    """

    # Subclasses should override these
    SOURCE_NAME: str = "unknown"
    CONFIG_KEY: str = ""  # Key used in settings.is_mock_mode()

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.SOURCE_NAME}")
        self._client: Optional[httpx.AsyncClient] = None
        self._is_mock: bool = self._check_mock_mode()
        self._last_fetch_ts: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._fetch_count: int = 0
        self._error_count: int = 0

        if self._is_mock:
            self.logger.warning(
                f"[{self.SOURCE_NAME}] API key not configured — running in MOCK mode"
            )

    # ── Public interface ──────────────────────────────────────────────────

    @abstractmethod
    async def fetch(self) -> dict[str, Any]:
        """Execute data fetch and return structured result.

        Returns:
            dict with at least:
                - "source": str — source name
                - "timestamp": str — ISO 8601 timestamp
                - "data": Any — fetched/parsed data
                - "is_mock": bool — whether mock data was returned
        """
        ...

    # ── HTTP client helpers ───────────────────────────────────────────────

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily create and return the shared HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.fetch_timeout_seconds),
                follow_redirects=True,
                headers={"User-Agent": f"MultiSourceResonance/3.1 ({self.SOURCE_NAME})"},
            )
        return self._client

    async def _get_json(
        self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None
    ) -> Any:
        """Perform a GET request and return parsed JSON."""
        client = await self._get_client()
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _post_json(
        self, url: str, json_body: Any, headers: Optional[dict] = None
    ) -> Any:
        """Perform a POST request and return parsed JSON."""
        client = await self._get_client()
        resp = await client.post(url, json=json_body, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ── Mock mode ─────────────────────────────────────────────────────────

    def _check_mock_mode(self) -> bool:
        """Determine whether to run in mock mode based on config."""
        if self.CONFIG_KEY:
            return settings.is_mock_mode(self.CONFIG_KEY)
        # No config key — always mock
        return True

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    # ── Result builder ────────────────────────────────────────────────────

    def _build_result(
        self, data: Any, extra: Optional[dict] = None
    ) -> dict[str, Any]:
        """Build a standardised result dict."""
        result = {
            "source": self.SOURCE_NAME,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
            "is_mock": self._is_mock,
        }
        if extra:
            result.update(extra)
        return result

    # ── Error tracking ────────────────────────────────────────────────────

    def _record_success(self) -> None:
        self._fetch_count += 1
        self._last_fetch_ts = datetime.now(timezone.utc)
        self._last_error = None

    def _record_error(self, error: str) -> None:
        self._error_count += 1
        self._last_error = error
        self.logger.error(f"[{self.SOURCE_NAME}] Fetch error: {error}")

    def get_status(self) -> dict[str, Any]:
        """Return current fetcher status for monitoring."""
        return {
            "source": self.SOURCE_NAME,
            "is_mock": self._is_mock,
            "fetch_count": self._fetch_count,
            "error_count": self._error_count,
            "last_fetch_ts": self._last_fetch_ts.isoformat() if self._last_fetch_ts else None,
            "last_error": self._last_error,
        }
