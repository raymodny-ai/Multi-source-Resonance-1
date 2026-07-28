"""
Security utilities: password hashing, API key leak detection, CORS hardening.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

import bcrypt

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Password hashing (bcrypt) — use bcrypt directly for compatibility
# ─────────────────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    pwd_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hash_bytes)


# ─────────────────────────────────────────────────────────────────────────────
# API Key leak detection
# ─────────────────────────────────────────────────────────────────────────────

# Patterns that look like hardcoded secrets in config / source files
_LEAK_PATTERNS = [
    re.compile(r"""(?:api_key|apikey|secret|password|token)\s*[:=]\s*["']([A-Za-z0-9_\-./+=]{16,})["']""", re.IGNORECASE),
    re.compile(r"""(?:sk|pk|key)[-_][A-Za-z0-9]{20,}"""),
]

# Files / directories to skip during scanning
_SCAN_IGNORE_DIRS = {".git", "__pycache__", ".venv", "node_modules", "dist", ".mypy_cache"}
_SCAN_IGNORE_EXTENSIONS = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".lock", ".png", ".jpg", ".gif"}


def scan_for_leaked_keys(directory: str | Path) -> list[dict]:
    """Scan a directory tree for hardcoded API keys / secrets.

    Returns a list of dicts with keys: file, line, match.
    """
    directory = Path(directory)
    findings: list[dict] = []

    if not directory.is_dir():
        logger.warning(f"Scan directory does not exist: {directory}")
        return findings

    for root, dirs, files in os.walk(directory):
        # Prune ignored directories
        dirs[:] = [d for d in dirs if d not in _SCAN_IGNORE_DIRS]

        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix.lower() in _SCAN_IGNORE_EXTENSIONS:
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except (OSError, PermissionError):
                continue

            for line_no, line in enumerate(content.splitlines(), start=1):
                # Skip comments
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                for pattern in _LEAK_PATTERNS:
                    matches = pattern.findall(line)
                    for m in matches:
                        # Skip placeholder / example values
                        if m.lower() in {"change-me-in-production", "changeme", "xxx", "your-key-here", "placeholder"}:
                            continue
                        findings.append({
                            "file": str(fpath.relative_to(directory)),
                            "line": line_no,
                            "match": m[:8] + "***",  # Truncate for safety
                        })

    if findings:
        logger.warning(f"API key leak scan found {len(findings)} potential leak(s)")
    else:
        logger.info("API key leak scan: no leaks detected")

    return findings


# ─────────────────────────────────────────────────────────────────────────────
# CORS security helpers
# ─────────────────────────────────────────────────────────────────────────────

def build_cors_config(
    origins: list[str],
    allow_credentials: bool = True,
    allow_methods: Optional[list[str]] = None,
    allow_headers: Optional[list[str]] = None,
) -> dict:
    """Build a hardened CORS configuration dict.

    Returns a dict suitable for passing to CORSMiddleware(**config).
    """
    return {
        "allow_origins": origins,
        "allow_credentials": allow_credentials,
        "allow_methods": allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": allow_headers or ["Authorization", "Content-Type", "X-Requested-With"],
    }
