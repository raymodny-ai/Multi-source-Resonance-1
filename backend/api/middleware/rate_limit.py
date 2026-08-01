"""API rate limiting middleware using slowapi.
Default: 100 requests/minute. Configurable per-endpoint via decorators.
"""

import logging
import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# SEC-08: when running behind a reverse proxy (nginx, ALB, Cloudflare)
# ``request.client.host`` is the proxy itself, not the real client.
# We honour ``X-Forwarded-For`` only when explicitly opted in via the
# environment variable ``MSR_TRUST_PROXY=1`` — otherwise an attacker
# could spoof their IP by setting the header themselves.
def _client_key(request) -> str:
    trust_proxy = os.environ.get("MSR_TRUST_PROXY", "").lower() in (
        "1", "true", "yes",
    )
    if trust_proxy:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            # First entry is the original client; rest are chained proxies.
            return fwd.split(",")[0].strip()
    return get_remote_address(request)


# ─────────────────────────────────────────────────────────────────────────────
# Limiter instance — attach to FastAPI app via init_rate_limiter()
# ─────────────────────────────────────────────────────────────────────────────

# SEC-07: in production we share state across workers via Redis so the
# 100/min limit is enforced cluster-wide. The env var
# ``MSR_REDIS_URL`` (e.g. ``redis://host:6379/0``) opts in; absent
# that, we fall back to in-memory storage which is fine for dev but
# not for multi-worker production.
_storage_uri = os.environ.get("MSR_REDIS_URL", "memory://")
limiter = Limiter(
    key_func=_client_key,
    default_limits=["100/minute"],
    storage_uri=_storage_uri,
)
if _storage_uri != "memory://":
    logger.info(f"Rate limiter using Redis storage: {_storage_uri}")
else:
    logger.warning(
        "FIX-SEC-07: rate limiter uses in-memory storage — single-process only. "
        "Set MSR_REDIS_URL=redis://host:6379/0 for cluster-wide limits."
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
