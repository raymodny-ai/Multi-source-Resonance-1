"""
Base fetcher class for all data source collectors.
Provides unified interface, retry logic, mock mode fallback, and data validation.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from backend.config import Settings

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """Abstract base class for all data source fetchers.

    Subclasses must implement:
        - source_name (property): human-readable data source identifier
        - fetch(): core data collection logic returning a dict
        - _mock_data(): return realistic mock data when API key is absent
    """

    def __init__(self, config: Settings, db: Any = None) -> None:
        """Initialize fetcher with application config and optional database handle.

        Args:
            config: Application Settings instance (contains API keys, timeouts, etc.)
            db: Database connection or manager instance (aiosqlite / DBManager)
        """
        self.config = config
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.{self.source_name}")
        self._http_client: Optional[httpx.AsyncClient] = None

    # ── Abstract interface ────────────────────────────────────────────────────

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name for this data source (e.g. 'GEXMetrix', 'VIX')."""
        ...

    @abstractmethod
    async def fetch(self) -> dict:
        """Execute data collection.

        Returns:
            dict with collected data conforming to the corresponding Pydantic model.
        """
        ...

    @abstractmethod
    def _mock_data(self) -> dict:
        """Return realistic mock data for this source.

        Used when API key is missing or explicit mock mode is enabled.
        The returned dict must conform to the corresponding Pydantic model schema.

        Returns:
            dict with mock data matching the real data structure.
        """
        ...

    # ── Timeout configuration ─────────────────────────────────────────────────

    @property
    def timeout(self) -> int:
        """HTTP request timeout in seconds, read from config."""
        return self.config.fetch_timeout_seconds

    # ── Mock mode detection ───────────────────────────────────────────────────

    def _is_mock_mode(self) -> bool:
        """Check whether this fetcher should operate in mock mode.

        Mock mode is activated when the required API key is absent from config.
        Subclasses can override `_mock_mode_key` to specify which config key to check.
        """
        return self.config.is_mock_mode(self._mock_mode_key)

    @property
    def _mock_mode_key(self) -> str:
        """Key used to look up mock mode status in config.is_mock_mode().

        Override in subclasses if the key differs from source_name.
        Default mapping: source_name -> config key.
        """
        # Default: use source_name lowercased
        name_map = {
            "gexmetrix": "gexmetrix",
            "axlfi": "axlfi",
            "vix": "gexmetrix",       # VIX uses CBOE public data, no key needed
            "yfinance": "gexmetrix",   # yfinance is public, no key needed
            "cboe": "gexmetrix",       # CBOE public data
        }
        return name_map.get(self.source_name.lower(), "gexmetrix")

    # ── Retry logic ───────────────────────────────────────────────────────────

    async def fetch_with_retry(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> dict:
        """Execute fetch with exponential backoff retry.

        On each failure, waits backoff_factor * 2^attempt seconds before retrying.
        If all retries fail or mock mode is active, falls back to mock data.

        Args:
            max_retries: Maximum number of retry attempts (default 3).
            backoff_factor: Base delay multiplier for exponential backoff (default 1.0s).

        Returns:
            dict with fetched or mock data, always includes '_meta' key.
        """
        # If mock mode, return mock data immediately
        if self._is_mock_mode():
            self.logger.info(f"[{self.source_name}] API key absent — returning mock data")
            return self._wrap_result(self._mock_data(), is_mock=True)

        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                self.logger.debug(
                    f"[{self.source_name}] Fetch attempt {attempt + 1}/{max_retries}"
                )
                data = await self.fetch()

                # Validate the fetched data
                if not self._validate_data(data):
                    raise ValueError(f"[{self.source_name}] Data validation failed")

                return self._wrap_result(data, is_mock=False)

            except Exception as exc:
                last_error = exc
                self.logger.warning(
                    f"[{self.source_name}] Attempt {attempt + 1} failed: {exc}"
                )
                if attempt < max_retries - 1:
                    delay = backoff_factor * (2 ** attempt)
                    self.logger.debug(f"[{self.source_name}] Retrying in {delay:.1f}s")
                    await asyncio.sleep(delay)

        # All retries exhausted — fall back to mock data
        self.logger.error(
            f"[{self.source_name}] All {max_retries} retries failed. "
            f"Last error: {last_error}. Falling back to mock data."
        )
        return self._wrap_result(self._mock_data(), is_mock=True, error=str(last_error))

    # ── Data validation ───────────────────────────────────────────────────────

    def _validate_data(self, data: dict) -> bool:
        """Validate fetched data structure and basic sanity checks.

        Override in subclasses for source-specific validation.
        Default implementation checks that data is a non-empty dict.

        Args:
            data: The raw data dict from fetch().

        Returns:
            True if data passes validation, False otherwise.
        """
        if not isinstance(data, dict):
            self.logger.warning(f"[{self.source_name}] Data is not a dict")
            return False
        if not data:
            self.logger.warning(f"[{self.source_name}] Data dict is empty")
            return False
        return True

    # ── HTTP client helper ────────────────────────────────────────────────────

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create a shared async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers={"User-Agent": "MultiSourceResonance/3.1"},
            )
        return self._http_client

    async def _http_get(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> httpx.Response:
        """Perform an async HTTP GET request.

        Args:
            url: Target URL.
            headers: Optional request headers.
            params: Optional query parameters.

        Returns:
            httpx.Response with the server reply.

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
            httpx.TimeoutException: On timeout.
        """
        client = await self._get_client()
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response

    async def close(self) -> None:
        """Close the HTTP client session."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # ── Result wrapping ───────────────────────────────────────────────────────

    def _wrap_result(
        self,
        data: dict,
        is_mock: bool = False,
        error: Optional[str] = None,
    ) -> dict:
        """Wrap fetch result with metadata.

        Args:
            data: The fetched or mock data.
            is_mock: Whether this is mock data.
            error: Error message if fetch failed.

        Returns:
            dict with '_meta' key containing collection metadata.
        """
        data["_meta"] = {
            "source": self.source_name,
            "is_mock": is_mock,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }
        return data
