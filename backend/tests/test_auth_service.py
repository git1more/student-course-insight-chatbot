"""
Unit tests — app/services/auth_service.py

Mocks user_repo and security helpers; no DB required.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.auth_service import AuthService
from app.db.models import User


@pytest.fixture
def svc():
    return AuthService()


@pytest.fixture
def db():
    return MagicMock()


def _user(id=1, email="u@x.com", role="user"):
    u = MagicMock(spec=User)
    u.id, u.email, u.role = id, email, role
    u.password_hash = "hashed"
    return u


# ── signup ────────────────────────────────────────────────────────────────────

class TestSignup:
    def test_returns_token_and_role(self, svc, db):
        with patch("app.services.auth_service.user_repo.create", return_value=_user()), \
             patch("app.services.auth_service.create_access_token", return_value="tok"):
            result = svc.signup(db, "new@x.com", "pass")
        assert result["access_token"] == "tok"
        assert result["role"] == "user"

    def test_duplicate_email_propagates(self, svc, db):
        with patch("app.services.auth_service.user_repo.create",
                   side_effect=ValueError("Email already registered")):
            with pytest.raises(ValueError, match="already registered"):
                svc.signup(db, "dup@x.com", "pass")

    def test_role_forwarded_to_repo(self, svc, db):
        u = _user(role="admin")
        with patch("app.services.auth_service.user_repo.create", return_value=u) as mock_create, \
             patch("app.services.auth_service.create_access_token", return_value="tok"):
            svc.signup(db, "a@x.com", "pass", role="admin")
        mock_create.assert_called_once_with(db, email="a@x.com", password="pass", role="admin")


# ── login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_success_returns_token_and_role(self, svc, db):
        with patch("app.services.auth_service.user_repo.get_by_email", return_value=_user(id=3)), \
             patch("app.services.auth_service.verify_password", return_value=True), \
             patch("app.services.auth_service.create_access_token", return_value="tok_ok"):
            result = svc.login(db, "u@x.com", "correct")
        assert result["access_token"] == "tok_ok"
        assert result["role"] == "user"

    def test_wrong_password_raises(self, svc, db):
        with patch("app.services.auth_service.user_repo.get_by_email", return_value=_user()), \
             patch("app.services.auth_service.verify_password", return_value=False):
            with pytest.raises(ValueError, match="Invalid email or password"):
                svc.login(db, "u@x.com", "wrong")

    def test_user_not_found_raises(self, svc, db):
        with patch("app.services.auth_service.user_repo.get_by_email", return_value=None):
            with pytest.raises(ValueError, match="Invalid email or password"):
                svc.login(db, "ghost@x.com", "any")

    def test_token_created_with_correct_subject(self, svc, db):
        u = _user(id=42, role="admin")
        with patch("app.services.auth_service.user_repo.get_by_email", return_value=u), \
             patch("app.services.auth_service.verify_password", return_value=True), \
             patch("app.services.auth_service.create_access_token", return_value="t") as mt:
            svc.login(db, "a@x.com", "pass")
        mt.assert_called_once_with(subject="42", role="admin")
