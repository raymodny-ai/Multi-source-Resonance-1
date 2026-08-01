"""
JWT authentication middleware and dependency injection for FastAPI.
Provides token creation, verification, and a dependency to extract the current user.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Token blacklist (in-memory; cleared on restart)
# ─────────────────────────────────────────────────────────────────────────────

_token_blacklist: set[str] = set()


def add_to_blacklist(jti: str) -> None:
    """Add a token JTI to the in-memory blacklist."""
    _token_blacklist.add(jti)


def is_blacklisted(jti: str) -> bool:
    """Check whether a token JTI has been revoked."""
    return jti in _token_blacklist


def get_blacklist_size() -> int:
    """Return the number of blacklisted tokens."""
    return len(_token_blacklist)


# ─────────────────────────────────────────────────────────────────────────────
# Token creation
# ─────────────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    Args:
        data: Payload claims (must include 'sub').
        expires_delta: Custom expiry; defaults to settings.jwt_expire_minutes.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "type": "access",
    })
    # FIX-05: route through the new ``effective_jwt_secret`` accessor so a
    # missing env var does not fall back to a hardcoded placeholder.
    return jwt.encode(to_encode, settings.effective_jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token (longer-lived, type='refresh').

    Args:
        data: Payload claims (must include 'sub').
        expires_delta: Custom expiry; defaults to 7 days.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=7)
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    })
    # FIX-05: same hardening as create_access_token.
    return jwt.encode(to_encode, settings.effective_jwt_secret, algorithm=settings.jwt_algorithm)


# ─────────────────────────────────────────────────────────────────────────────
# Token verification
# ─────────────────────────────────────────────────────────────────────────────

def verify_token(token: str, expected_type: str = "access") -> dict:
    """Decode and verify a JWT token.

    Args:
        token: Raw JWT string.
        expected_type: 'access' or 'refresh'.

    Returns:
        Decoded payload dict.

    Raises:
        HTTPException 401 if token is invalid, expired, or blacklisted.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.effective_jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        # Check token type
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type: expected {expected_type}",
            )
        # Check blacklist
        jti = payload.get("jti")
        if jti and is_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
        return payload
    except JWTError as e:
        logger.debug(f"Token verification failed: {e}")
        raise credentials_exception


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI dependency: extract current user from Bearer token
# ─────────────────────────────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> dict:
    """FastAPI dependency to extract and validate the current user from the Authorization header.

    Returns:
        Dict with 'sub' (username), 'jti', and other claims.

    Raises:
        HTTPException 401 if no valid token is present.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(credentials.credentials, expected_type="access")


# ─────────────────────────────────────────────────────────────────────────────
# Middleware: protect all write endpoints (PUT, POST, DELETE)
# ─────────────────────────────────────────────────────────────────────────────

# Paths that are exempt from JWT protection (public endpoints)
_PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/ws",
}

# Path prefixes that are public
_PUBLIC_PREFIXES = ("/docs", "/redoc", "/openapi.json")

# FIX-09: sensitive GET endpoints that must NOT be public. These expose
# raw pipeline metrics, config secrets, or admin-only state — they were
# previously reachable without any token, allowing unauthenticated
# scraping of internal state. Each entry is an exact path match.
#
# Owner decision 2026-08-02 (方案 C): exempt the two read-only endpoints the
# React dashboard NEEDS to render (source connectivity + recent logs) back to
# public GET. They carry no secrets — source-status is source health flags,
# logs is the in-memory log ring. config / metrics / recent-alerts / etc.
# remain JWT-protected (true admin/sensitive state).
_SENSITIVE_GET_PATHS: set[str] = {
    "/api/system/pipeline-status",
    # "/api/system/source-status",  # exempt on purpose — dashboard SourceHealthGrid renders this
    # "/api/system/logs",            # exempt on purpose — SystemView renders this
    "/api/config",
    "/api/config/",
    "/api/metrics/pipeline",
    "/api/metrics/eventbus",
    "/api/signals/recent-alerts",
    "/api/analysis/recent",
    "/api/options-greeks/positions",
}


def _is_sensitive_get(request: Request) -> bool:
    """FIX-09 helper: identify sensitive GET endpoints that require auth.

    A GET is considered sensitive when its path is in the explicit list, or
    matches a known admin-only prefix. We deliberately keep the public read
    surface (dashboard, history, gex-curve, ...) accessible without a token
    so existing frontends keep working.
    """
    path = request.url.path
    if path in _SENSITIVE_GET_PATHS:
        return True
    sensitive_prefixes = (
        "/api/admin",
        "/api/internal",
        "/api/secrets",
    )
    return any(path.startswith(p) for p in sensitive_prefixes)


async def jwt_write_middleware(request: Request, call_next):
    """ASGI middleware enforcing JWT for write operations AND sensitive GETs.

    FIX-08: keeps POST/PUT/DELETE protected.
    FIX-09: also protects a hand-curated list of admin/sensitive GET endpoints
    that previously returned pipeline internals without any authentication.
    """
    # Allow all GET / HEAD / OPTIONS requests through, unless this GET is
    # on the sensitive list (FIX-09).
    if request.method == "GET":
        if not _is_sensitive_get(request):
            return await call_next(request)
    elif request.method in ("HEAD", "OPTIONS"):
        return await call_next(request)

    # Check if path is public (applies to writes only; sensitive GETs above
    # already passed the gate so we never hit this for them).
    path = request.url.path
    if path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return await call_next(request)

    # Require valid access token for write operations and sensitive GETs
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
        )

    token = auth_header[7:]
    try:
        verify_token(token, expected_type="access")
    except HTTPException:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"},
        )

    return await call_next(request)


