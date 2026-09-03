"""
Security utilities — password hashing and JWT token management.

Passwords are hashed with PBKDF2-SHA256 (via passlib).
Tokens are signed HS256 JWTs (via python-jose).
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

# Use PBKDF2-SHA256; bcrypt is avoided here because passlib's bcrypt
# implementation requires an additional native dependency on some platforms.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a salted hash of *password* suitable for database storage."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*.

    Returns False (rather than raising) for any invalid or unrecognised hash
    string, preventing information leakage through exception messages.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # passlib raises UnknownHashError for malformed hashes.
        return False


def create_access_token(
    subject: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create and return a signed JWT access token.

    Args:
        subject:       The user's database ID (stored as the ``sub`` claim).
        role:          The user's role (``"user"`` or ``"admin"``).
        expires_delta: Custom lifetime; defaults to *settings.access_token_expire_minutes*.

    Returns:
        A compact, URL-safe JWT string.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,   # subject — user ID
        "role": role,     # custom claim for RBAC
        "exp": expire,    # expiry timestamp (checked by python-jose on decode)
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token.

    Args:
        token: A compact JWT string.

    Returns:
        The decoded payload dictionary.

    Raises:
        ValueError: If the token is expired, tampered with, or otherwise invalid.
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
