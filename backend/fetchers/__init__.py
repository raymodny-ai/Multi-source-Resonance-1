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

# New fetchers (v3.1 modular expansion)
from backend.fetchers.squeezemetrics_fetcher import SqueezeMetricsFetcher
from backend.fetchers.finra_fetcher import FinraFetcher
from backend.fetchers.ccdata_fetcher import CCDataFetcher
from backend.fetchers.stockgrid_fetcher import StockGridFetcher
from backend.fetchers.coinglass_fetcher import CoinglassFetcher
from backend.fetchers.tradier_fetcher import TradierFetcher
from backend.fetchers.dbmf_fetcher import DBMFFetcher

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
    # New fetchers
    "SqueezeMetricsFetcher",
    "FinraFetcher",
    "CCDataFetcher",
    "StockGridFetcher",
    "CoinglassFetcher",
    "TradierFetcher",
    "DBMFFetcher",
]
