"""
Authentication routes: login, refresh, logout.
Manages JWT token lifecycle with in-memory blacklist + database persistence.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.api.middleware.auth import (
    add_to_blacklist,
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_token,
)
from backend.api.middleware.rate_limit import AUTH_LIMIT, limiter
from backend.database import get_db
from backend.utils.security import verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    token: Optional[str] = None  # access token to revoke


class MessageResponse(BaseModel):
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# Database-backed user authentication
# ─────────────────────────────────────────────────────────────────────────────

async def _verify_user(username: str, password: str) -> bool:
    """Verify active user credentials against the database.

    FIX-05: no built-in account exists; administrators are seeded into the
    ``users`` table from explicit ``MSR_ADMIN_*`` configuration.
    """
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT password_hash
            FROM users
            WHERE username = ? AND is_active = 1
            """,
            (username,),
        )
        row = await cursor.fetchone()

    if row is None:
        return False
    return verify_password(password, row["password_hash"])


# ─────────────────────────────────────────────────────────────────────────────
# Token blacklist persistence (database-backed)
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_blacklist_table() -> None:
    """Create the token_blacklist table if it doesn't exist."""
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS token_blacklist (
                jti TEXT PRIMARY KEY,
                revoked_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


async def _persist_blacklist(jti: str) -> None:
    """Persist a blacklisted JTI to the database."""
    try:
        async with get_db() as db:
            await db.execute(
                "INSERT OR IGNORE INTO token_blacklist (jti) VALUES (?)",
                (jti,),
            )
    except Exception as e:
        logger.warning(f"Failed to persist blacklist entry: {e}")


async def _load_blacklist_from_db() -> None:
    """Load all blacklisted JTIs from database into memory on startup."""
    try:
        async with get_db() as db:
            cursor = await db.execute("SELECT jti FROM token_blacklist")
            rows = await cursor.fetchall()
            for row in rows:
                add_to_blacklist(row["jti"])
            if rows:
                logger.info(f"Loaded {len(rows)} blacklisted tokens from database")
    except Exception as e:
        logger.debug(f"No blacklist table yet (first run): {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
@limiter.limit(AUTH_LIMIT)
async def login(request: Request, body: LoginRequest):
    """Authenticate user and return JWT access + refresh tokens."""
    if not await _verify_user(body.username, body.password):
        logger.warning(f"Failed login attempt for user: {body.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token_data = {"sub": body.username}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.info(f"User '{body.username}' logged in successfully")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(AUTH_LIMIT)
async def refresh(request: Request, body: RefreshRequest):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    payload = verify_token(body.refresh_token, expected_type="refresh")

    # Revoke old refresh token (rotation)
    jti = payload.get("jti")
    if jti:
        add_to_blacklist(jti)
        await _persist_blacklist(jti)

    # Issue new tokens
    token_data = {"sub": payload.get("sub")}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    body: LogoutRequest,
    current_user: dict = Depends(get_current_user),
):
    """Revoke the current access token (add to blacklist)."""
    # Blacklist the current token
    if body.token:
        try:
            payload = verify_token(body.token, expected_type="access")
            jti = payload.get("jti")
            if jti:
                add_to_blacklist(jti)
                await _persist_blacklist(jti)
        except HTTPException:
            pass  # Token already invalid/expired

    # Also blacklist via jti from current_user context if available
    jti = current_user.get("jti")
    if jti:
        add_to_blacklist(jti)
        await _persist_blacklist(jti)

    logger.info(f"User '{current_user.get('sub')}' logged out")
    return MessageResponse(message="Successfully logged out")


# ─────────────────────────────────────────────────────────────────────────────
# Startup hook: load blacklist from DB
# ─────────────────────────────────────────────────────────────────────────────

async def init_auth() -> None:
    """Call on application startup to initialize auth subsystem."""
    await _ensure_blacklist_table()
    await _load_blacklist_from_db()
    logger.info("Auth subsystem initialized")
