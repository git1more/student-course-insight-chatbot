"""
Unit tests — app/routers/admin.py

Covers: user listing, role toggle, self-demotion guard, delete, delete-self guard,
analytics, and logs endpoints. All DB / repo calls are mocked.
"""
import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import make_auth_header
from app.db.models import User


def _admin_user(id=1):
    u = MagicMock(spec=User)
    u.id, u.role, u.email = id, "admin", "admin@example.com"
    return u


def _regular_user(id=2):
    u = MagicMock(spec=User)
    u.id, u.role, u.email = id, "user", "user@example.com"
    u.created_at.isoformat.return_value = "2024-01-01T00:00:00"
    return u


def _setup_admin_auth(mock_db, admin_id=1):
    """Make mock_db return admin user for the require_admin dependency lookup."""
    admin = _admin_user(admin_id)
    mock_db.query.return_value.filter.return_value.first.return_value = admin
    return admin


# ── GET /admin/users ──────────────────────────────────────────────────────────

class TestListUsers:
    def test_admin_can_list_users(self, client, mock_db):
        _setup_admin_auth(mock_db)
        users = [_regular_user(2), _regular_user(3)]
        for u in users:
            u.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        headers = make_auth_header(subject="1", role="admin")
        with patch("app.routers.admin.user_repo.get_all", return_value=users):
            r = client.get("/admin/users", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_non_admin_gets_403(self, client, mock_db):
        u = MagicMock(spec=User)
        u.id, u.role = 2, "user"
        mock_db.query.return_value.filter.return_value.first.return_value = u
        headers = make_auth_header(subject="2", role="user")
        r = client.get("/admin/users", headers=headers)
        assert r.status_code == 403

    def test_unauthenticated_gets_403(self, client, mock_db):
        r = client.get("/admin/users")
        assert r.status_code == 403


# ── PATCH /admin/users/{id}/role ──────────────────────────────────────────────

class TestUpdateRole:
    def test_toggle_user_to_admin(self, client, mock_db):
        _setup_admin_auth(mock_db, admin_id=1)
        target = _regular_user(2)
        target.role = "admin"
        headers = make_auth_header(subject="1", role="admin")
        with patch("app.routers.admin.user_repo.update_role", return_value=target):
            r = client.patch("/admin/users/2/role",
                             json={"role": "admin"}, headers=headers)
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_cannot_change_own_role(self, client, mock_db):
        """Admin must not be able to demote themselves."""
        _setup_admin_auth(mock_db, admin_id=1)
        headers = make_auth_header(subject="1", role="admin")
        r = client.patch("/admin/users/1/role",
                         json={"role": "user"}, headers=headers)
        assert r.status_code == 400
        assert "own role" in r.json()["detail"]

    def test_invalid_role_value_returns_400(self, client, mock_db):
        _setup_admin_auth(mock_db, admin_id=1)
        headers = make_auth_header(subject="1", role="admin")
        r = client.patch("/admin/users/2/role",
                         json={"role": "superuser"}, headers=headers)
        assert r.status_code == 400

    def test_user_not_found_returns_404(self, client, mock_db):
        _setup_admin_auth(mock_db, admin_id=1)
        headers = make_auth_header(subject="1", role="admin")
        with patch("app.routers.admin.user_repo.update_role",
                   side_effect=ValueError("User not found")):
            r = client.patch("/admin/users/999/role",
                             json={"role": "admin"}, headers=headers)
        assert r.status_code == 404


# ── DELETE /admin/users/{id} ──────────────────────────────────────────────────

class TestDeleteUser:
    def test_admin_can_delete_other_user(self, client, mock_db):
        _setup_admin_auth(mock_db, admin_id=1)
        headers = make_auth_header(subject="1", role="admin")
        with patch("app.routers.admin.user_repo.delete"):
            r = client.delete("/admin/users/2", headers=headers)
        assert r.status_code == 200
        assert "deleted" in r.json()["message"]

    def test_cannot_delete_self(self, client, mock_db):
        _setup_admin_auth(mock_db, admin_id=1)
        headers = make_auth_header(subject="1", role="admin")
        r = client.delete("/admin/users/1", headers=headers)
        assert r.status_code == 400
        assert "own account" in r.json()["detail"]

    def test_delete_nonexistent_user_returns_404(self, client, mock_db):
        _setup_admin_auth(mock_db, admin_id=1)
        headers = make_auth_header(subject="1", role="admin")
        with patch("app.routers.admin.user_repo.delete",
                   side_effect=ValueError("User not found")):
            r = client.delete("/admin/users/999", headers=headers)
        assert r.status_code == 404

    def test_non_admin_cannot_delete(self, client, mock_db):
        u = MagicMock(spec=User)
        u.id, u.role = 2, "user"
        mock_db.query.return_value.filter.return_value.first.return_value = u
        headers = make_auth_header(subject="2", role="user")
        r = client.delete("/admin/users/3", headers=headers)
        assert r.status_code == 403


# ── GET /admin/analytics ──────────────────────────────────────────────────────

class TestAnalytics:
    def test_returns_analytics_data(self, client, mock_db):
        _setup_admin_auth(mock_db, admin_id=1)
        headers = make_auth_header(subject="1", role="admin")
        analytics = {
            "total_queries": 50, "ok_queries": 40, "blocked_queries": 10,
            "avg_duration_ms": 350.0, "most_queried_courses": [], "status_breakdown": []
        }
        with patch("app.routers.admin.analytics_service.get_admin_analytics",
                   return_value=analytics):
            r = client.get("/admin/analytics", headers=headers)
        assert r.status_code == 200
        assert r.json()["total_queries"] == 50
