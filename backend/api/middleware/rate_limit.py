"""
API rate limiting middleware using slowapi.
Default: 100 requests/minute. Configurable per-endpoint via decorators.
"""

import logging

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Limiter instance — attach to FastAPI app via init_rate_limiter()
# ─────────────────────────────────────────────────────────────────────────────

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="memory://",
)


def init_rate_limiter(app) -> None:
    """Register the rate limiter middleware and exception handler on a FastAPI app.

    Call this after creating the FastAPI instance but before registering routes.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiter initialized: default 100 requests/minute")


# ─────────────────────────────────────────────────────────────────────────────
# Per-endpoint limit presets (use as decorators on route functions)
# ─────────────────────────────────────────────────────────────────────────────

# Strict limit for auth endpoints (prevent brute-force)
AUTH_LIMIT = "10/minute"

# Moderate limit for write operations
WRITE_LIMIT = "30/minute"

# Relaxed limit for data collection triggers
COLLECTION_LIMIT = "5/minute"

# Health / status endpoints are excluded (no limit)
# Use @limiter.exempt on those routes if needed
