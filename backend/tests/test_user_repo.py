"""
Unit tests — app/repositories/user_repo.py

All SQLAlchemy calls are replaced with MagicMock, so no database is needed.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.repositories.user_repo import UserRepository
from app.db.models import User


@pytest.fixture
def repo():
    return UserRepository()


@pytest.fixture
def db():
    return MagicMock()


def _user(id=1, email="test@example.com", role="user"):
    u = MagicMock(spec=User)
    u.id = id
    u.email = email
    u.role = role
    u.password_hash = "hashed"
    return u


# ── create ────────────────────────────────────────────────────────────────────

class TestCreate:
    def test_new_user_calls_add_commit_refresh(self, repo, db):
        db.query.return_value.filter.return_value.first.return_value = None
        with patch("app.repositories.user_repo.hash_password", return_value="hp"):
            repo.create(db, "new@example.com", "pass")
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_duplicate_email_raises_value_error(self, repo, db):
        db.query.return_value.filter.return_value.first.return_value = _user()
        with pytest.raises(ValueError, match="already registered"):
            repo.create(db, "dup@example.com", "pass")

    def test_role_defaults_to_user(self, repo, db):
        db.query.return_value.filter.return_value.first.return_value = None
        captured = {}
        def fake_add(obj):
            captured["user"] = obj
        db.add.side_effect = fake_add
        with patch("app.repositories.user_repo.hash_password", return_value="hp"):
            repo.create(db, "x@x.com", "pass")
        assert captured["user"].role == "user"


# ── get_by_email ──────────────────────────────────────────────────────────────

class TestGetByEmail:
    def test_returns_user_when_found(self, repo, db):
        u = _user(email="found@x.com")
        db.query.return_value.filter.return_value.first.return_value = u
        assert repo.get_by_email(db, "found@x.com") is u

    def test_returns_none_when_missing(self, repo, db):
        db.query.return_value.filter.return_value.first.return_value = None
        assert repo.get_by_email(db, "ghost@x.com") is None


# ── get_by_id ─────────────────────────────────────────────────────────────────

class TestGetById:
    def test_returns_user_when_found(self, repo, db):
        u = _user(id=7)
        db.query.return_value.filter.return_value.first.return_value = u
        assert repo.get_by_id(db, 7) is u

    def test_returns_none_when_missing(self, repo, db):
        db.query.return_value.filter.return_value.first.return_value = None
        assert repo.get_by_id(db, 999) is None


# ── update_role ───────────────────────────────────────────────────────────────

class TestUpdateRole:
    def test_role_changes_and_commits(self, repo, db):
        u = _user(role="user")
        db.query.return_value.filter.return_value.first.return_value = u
        repo.update_role(db, 1, "admin")
        assert u.role == "admin"
        db.commit.assert_called_once()

    def test_user_not_found_raises(self, repo, db):
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="User not found"):
            repo.update_role(db, 999, "admin")


# ── delete ────────────────────────────────────────────────────────────────────

class TestDelete:
    def test_delete_calls_db_delete_and_commit(self, repo, db):
        u = _user(id=2)
        db.query.return_value.filter.return_value.first.return_value = u
        repo.delete(db, 2)
        db.delete.assert_called_once_with(u)
        db.commit.assert_called_once()

    def test_delete_user_not_found_raises(self, repo, db):
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="User not found"):
            repo.delete(db, 999)


# ── get_all ───────────────────────────────────────────────────────────────────

class TestGetAll:
    def test_returns_all_users(self, repo, db):
        users = [_user(i) for i in range(3)]
        db.query.return_value.order_by.return_value.all.return_value = users
        assert repo.get_all(db) == users
