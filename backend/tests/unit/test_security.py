"""
Unit tests for security utilities: password hashing, verification,
JWT token generation/verification, token blacklist, and CORS config.
"""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from backend.api.middleware.auth import (
    add_to_blacklist,
    create_access_token,
    create_refresh_token,
    get_blacklist_size,
    is_blacklisted,
    verify_token,
    _token_blacklist,
)
from backend.utils.security import (
    build_cors_config,
    hash_password,
    verify_password,
)


# ===========================================================================
# Password hashing
# ===========================================================================

class TestPasswordHashing:

    def test_hash_and_verify(self):
        hashed = hash_password("my_secret_password")
        assert hashed != "my_secret_password"
        assert verify_password("my_secret_password", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        # bcrypt uses random salt, so hashes should differ
        assert h1 != h2
        # But both should verify
        assert verify_password("same_password", h1)
        assert verify_password("same_password", h2)

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False


# ===========================================================================
# JWT token creation and verification
# ===========================================================================

class TestJWTTokens:

    def test_create_access_token(self):
        token = create_access_token({"sub": "admin"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_create_refresh_token(self):
        token = create_refresh_token({"sub": "admin"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_verify_access_token(self):
        token = create_access_token({"sub": "testuser"})
        payload = verify_token(token, expected_type="access")
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_verify_refresh_token(self):
        token = create_refresh_token({"sub": "testuser"})
        payload = verify_token(token, expected_type="refresh")
        assert payload["sub"] == "testuser"
        assert payload["type"] == "refresh"

    def test_wrong_type_raises_401(self):
        token = create_access_token({"sub": "testuser"})
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, expected_type="refresh")
        assert exc_info.value.status_code == 401

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.jwt.token", expected_type="access")
        assert exc_info.value.status_code == 401

    def test_custom_expiry(self):
        token = create_access_token(
            {"sub": "admin"},
            expires_delta=timedelta(seconds=1),
        )
        payload = verify_token(token, expected_type="access")
        assert payload["sub"] == "admin"

    def test_access_token_has_jti(self):
        token = create_access_token({"sub": "admin"})
        payload = verify_token(token, expected_type="access")
        assert "jti" in payload
        assert len(payload["jti"]) > 0  # UUID format


# ===========================================================================
# Token blacklist
# ===========================================================================

class TestTokenBlacklist:

    def setup_method(self):
        """Clear blacklist before each test."""
        _token_blacklist.clear()

    def test_add_and_check(self):
        add_to_blacklist("test-jti-123")
        assert is_blacklisted("test-jti-123") is True
        assert is_blacklisted("nonexistent") is False

    def test_blacklist_size(self):
        add_to_blacklist("jti-1")
        add_to_blacklist("jti-2")
        add_to_blacklist("jti-3")
        assert get_blacklist_size() == 3

    def test_blacklisted_token_rejected(self):
        token = create_access_token({"sub": "admin"})
        payload = verify_token(token, expected_type="access")
        jti = payload["jti"]

        # Before blacklisting — should work
        verify_token(token, expected_type="access")

        # After blacklisting — should raise 401
        add_to_blacklist(jti)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, expected_type="access")
        assert exc_info.value.status_code == 401

    def test_duplicate_blacklist(self):
        add_to_blacklist("same-jti")
        add_to_blacklist("same-jti")
        assert get_blacklist_size() == 1


# ===========================================================================
# CORS config builder
# ===========================================================================

class TestCORSConfig:

    def test_default_config(self):
        config = build_cors_config(["http://localhost:5173"])
        assert config["allow_origins"] == ["http://localhost:5173"]
        assert config["allow_credentials"] is True
        assert "GET" in config["allow_methods"]
        assert "Authorization" in config["allow_headers"]

    def test_custom_methods(self):
        config = build_cors_config(
            ["http://localhost:3000"],
            allow_methods=["GET", "POST"],
        )
        assert config["allow_methods"] == ["GET", "POST"]

    def test_no_credentials(self):
        config = build_cors_config(
            ["*"],
            allow_credentials=False,
        )
        assert config["allow_credentials"] is False
