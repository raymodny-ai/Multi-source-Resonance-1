"""
Market sentiment data fetcher.

Collects sentiment indicators from real public sources:
- CNN Fear & Greed Index (free, no key) — primary
- Alternative.me Crypto Fear & Greed Index (free, no key) — secondary
- AAII survey is private (paid) so falls back to neutral

If both real sources fail the fetcher falls back to mock data with
``is_mock=True`` so the rest of the pipeline can flag it.

FIX-11: previous version was hardcoded to return mock data with no
real-data path. Now we always attempt real fetches first; mock is the
last resort, not the default.
"""

import random
from datetime import datetime, timezone
from typing import Any

from backend.fetchers.base import BaseFetcher


class SentimentFetcher(BaseFetcher):
    """Fetches market sentiment indicators from public APIs (no key needed)."""

    @property
    def source_name(self) -> str:
        return "market_sentiment"

    @property
    def _mock_mode_key(self) -> str:
        # Public APIs — no dedicated key in config. We DO try real first.
        # This key is only checked by the base ``_is_mock_mode`` shortcut
        # (which now correctly returns False for sources not in key_map),
        # so the live path is attempted regardless.
        return "gexmetrix"

    CNN_FNG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    ALTME_FNG_URL = "https://api.alternative.me/fng/?limit=1&format=json"

    async def fetch(self) -> dict:
        """Fetch sentiment data, attempting real APIs first.

        FIX-11: previously this method unconditionally returned mock data
        with ``_internal_mock=True``. We now try two free APIs and only
        fall back to mock when both fail.
        """
        # Try CNN Fear & Greed first
        cnn_data = await self._fetch_cnn_fng()
        if cnn_data is not None:
            return self._build_result(cnn_data, source="cnn_fng")

        # Try Alternative.me as a backup
        alt_data = await self._fetch_altme_fng()
        if alt_data is not None:
            return self._build_result(alt_data, source="alternative_me")

        # Both failed → mock fallback
        self.logger.warning("Sentiment: both real APIs failed, returning mock")
        return self._mock_data()

    def _mock_data(self) -> dict:
        """Return mock sentiment data (fallback only).

        Returns the dict without ``_meta`` — the base class wraps it via
        ``_wrap_result`` which sets ``is_mock=True, mock_reason="api_key_absent"``
        when called from ``fetch_with_retry``. Direct callers must wrap
        themselves.
        """
        return self._generate_mock_data()

    async def _fetch_cnn_fng(self) -> dict[str, Any] | None:
        """Fetch the CNN Fear & Greed Index (free, no key)."""
        try:
            client = await self._get_client()
            resp = await client.get(
                self.CNN_FNG_URL,
                headers={
                    "User-Agent": "MultiSourceResonance/3.1",
                    "Accept": "application/json",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            score = data.get("fear_and_greed", {}).get("score")
            rating = data.get("fear_and_greed", {}).get("rating")
            if score is None:
                return None
            return {
                "fear_greed_score": float(score),
                "fear_greed_label": str(rating).lower() if rating else None,
            }
        except Exception as exc:
            self.logger.debug(f"CNN FNG fetch failed: {exc}")
            return None

    async def _fetch_altme_fng(self) -> dict[str, Any] | None:
        """Fetch Alternative.me Crypto Fear & Greed Index (free, no key)."""
        try:
            client = await self._get_client()
            resp = await client.get(
                self.ALTME_FNG_URL,
                headers={"User-Agent": "MultiSourceResonance/3.1"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            row = (data.get("data") or [None])[0]
            if not row:
                return None
            value = row.get("value")
            classification = row.get("value_classification")
            if value is None:
                return None
            return {
                "fear_greed_score": float(value),
                "fear_greed_label": str(classification).lower() if classification else None,
            }
        except Exception as exc:
            self.logger.debug(f"Altme FNG fetch failed: {exc}")
            return None

    def _build_result(self, fng: dict[str, Any], source: str) -> dict[str, Any]:
        """Compose the full sentiment dict from a real Fear & Greed reading.

        The real fetches only give us the headline number; the rest of the
        fields (AAII, social, etc.) genuinely have no public source, so we
        mark them as ``source: "n/a"`` rather than fabricating them. This
        is FIX-13: do not inject random numbers into the real-data path.
        """
        score = float(fng.get("fear_greed_score", 50.0))
        label = fng.get("fear_greed_label") or _regime_from_score(score)
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fear_greed_index": round(score, 1),
            "fear_greed_label": label,
            # FIX-13: these have no real source. Mark them as unavailable
            # instead of generating random values that look real.
            "aaii_bull_pct": None,
            "aaii_bear_pct": None,
            "aaii_neutral_pct": None,
            "put_call_sentiment": "n/a",
            "social_sentiment_score": None,
            "news_sentiment_score": None,
            "vix_level": None,
            "is_extreme_sentiment": score < 20 or score > 80,
            "contrarian_signal": score < 25,
            "data_source": source,  # FIX-11: real-data provenance
        }

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock sentiment data (last-resort fallback)."""
        fear_greed = random.uniform(15, 85)
        aaii_bull = random.uniform(20, 55)
        aaii_bear = random.uniform(20, 55)

        # Derive composite sentiment
        if fear_greed < 25:
            regime = "extreme_fear"
        elif fear_greed < 40:
            regime = "fear"
        elif fear_greed < 60:
            regime = "neutral"
        elif fear_greed < 75:
            regime = "greed"
        else:
            regime = "extreme_greed"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fear_greed_index": round(fear_greed, 1),
            "fear_greed_label": regime,
            "aaii_bull_pct": round(aaii_bull, 1),
            "aaii_bear_pct": round(aaii_bear, 1),
            "aaii_neutral_pct": round(100 - aaii_bull - aaii_bear, 1),
            "put_call_sentiment": random.choice(["bearish", "neutral", "bullish"]),
            "social_sentiment_score": round(random.uniform(-1.0, 1.0), 3),
            "news_sentiment_score": round(random.uniform(-0.5, 0.5), 3),
            "vix_level": round(random.uniform(12, 35), 2),
            "is_extreme_sentiment": fear_greed < 20 or fear_greed > 80,
            "contrarian_signal": fear_greed < 25,
            "data_source": "mock",
        }


def _regime_from_score(score: float) -> str:
    """Map a numeric Fear & Greed score to a regime label."""
    if score < 25:
        return "extreme_fear"
    if score < 40:
        return "fear"
    if score < 60:
        return "neutral"
    if score < 75:
        return "greed"
    return "extreme_greed"
