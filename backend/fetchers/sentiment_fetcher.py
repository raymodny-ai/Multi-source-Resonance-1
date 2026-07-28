"""
Market sentiment data fetcher.

Collects sentiment indicators: Fear & Greed Index, put/call sentiment,
AAII survey, social media sentiment scores.
Always runs in mock mode (no dedicated free API for sentiment composites).
"""

import random
from datetime import datetime, timezone
from typing import Any

from backend.fetchers.base import BaseFetcher


class SentimentFetcher(BaseFetcher):
    """Fetches market sentiment indicators."""

    @property
    def source_name(self) -> str:
        return "market_sentiment"

    @property
    def _mock_mode_key(self) -> str:
        return ""  # Always mock

    async def fetch(self) -> dict:
        """Fetch sentiment data."""
        return self._generate_mock_data()

    def _mock_data(self) -> dict:
        """Return mock sentiment data."""
        return self._generate_mock_data()

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock sentiment data."""
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
            "contrarian_signal": fear_greed < 25,  # Extreme fear = contrarian buy
        }
