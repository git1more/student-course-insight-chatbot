"""
Unit tests — app/core/security.py

Covers: password hashing, password verification, JWT creation and decoding.
No database or external services required.
"""
import pytest
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


# ── Password hashing ─────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_returns_string(self):
        assert isinstance(hash_password("secret123"), str)

    def test_hash_is_not_plaintext(self):
        assert hash_password("secret123") != "secret123"

    def test_correct_password_verifies(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password_hashes_and_verifies(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_same_password_produces_different_hashes(self):
        """Salted hashing: two calls must not produce identical output."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_wrong_hash_fails_gracefully(self):
        """Invalid hash string should return False, not raise an exception."""
        result = verify_password("password", "not-a-valid-hash")
        assert result is False


# ── JWT ───────────────────────────────────────────────────────────────────────

class TestJWT:
    def test_token_is_non_empty_string(self):
        token = create_access_token(subject="42", role="user")
        assert isinstance(token, str) and len(token) > 0

    def test_decode_subject_matches(self):
        token = create_access_token(subject="99", role="user")
        assert decode_token(token)["sub"] == "99"

    def test_decode_role_matches(self):
        token = create_access_token(subject="1", role="admin")
        assert decode_token(token)["role"] == "admin"

    def test_token_contains_expiry(self):
        token = create_access_token(subject="1", role="user")
        assert "exp" in decode_token(token)

    def test_custom_expiry_accepted(self):
        token = create_access_token(subject="5", role="user", expires_delta=timedelta(days=7))
        assert decode_token(token)["sub"] == "5"

    def test_invalid_token_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token("not.a.real.token")

    def test_tampered_signature_raises(self):
        token = create_access_token(subject="1", role="user")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(ValueError):
            decode_token(tampered)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            decode_token("")
