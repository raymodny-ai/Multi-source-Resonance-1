"""
Data fetchers package — crypto, darkpool, flow, sentiment, LLM, and alternative data sources.

All fetchers inherit from BaseFetcher (base_alt.py) and expose a unified
`async fetch() -> dict` interface. When API keys are absent, fetchers
automatically operate in mock mode with realistic synthetic data.
"""

from backend.fetchers.base_alt import BaseFetcher
from backend.fetchers.crypto_fetcher import CryptoFetcher
from backend.fetchers.darkpool_fetcher import DarkpoolFetcher
from backend.fetchers.flow_fetcher import FlowFetcher
from backend.fetchers.llm_fetcher import LLMFetcher
from backend.fetchers.macro_fetcher import MacroFetcher
from backend.fetchers.put_call_fetcher import PutCallFetcher
from backend.fetchers.sector_fetcher import SectorFetcher
from backend.fetchers.sentiment_fetcher import SentimentFetcher
from backend.fetchers.vix_term_fetcher import VIXTermFetcher

__all__ = [
    "BaseFetcher",
    "CryptoFetcher",
    "DarkpoolFetcher",
    "FlowFetcher",
    "LLMFetcher",
    "MacroFetcher",
    "PutCallFetcher",
    "SectorFetcher",
    "SentimentFetcher",
    "VIXTermFetcher",
]
