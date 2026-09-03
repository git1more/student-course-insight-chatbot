"""
Integration tests — full HTTP request flows spanning multiple components.

Unlike unit tests, these exercise the complete request/response cycle:
  router → dependency injection → service → (mocked) repository

External dependencies (OpenAI, real DB) are still mocked, but the
full FastAPI middleware stack (auth, CORS, error handling) is active.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.db.models import User, QueryLog


def _make_user(id=1, email="user@example.com", role="user"):
    u = MagicMock(spec=User)
    u.id, u.email, u.role = id, email, role
    u.password_hash = "hashed"
    u.created_at.isoformat.return_value = "2024-01-01T00:00:00"
    return u


def _make_log(id=1, user_id=1, question="Test?", course_code="CS", term="2024"):
    log = MagicMock(spec=QueryLog)
    log.id, log.user_id = id, user_id
    log.question, log.course_code, log.term = question, course_code, term
    log.duration_ms, log.result_count, log.status = 200, 5, "ok"
    log.result_json = None
    log.created_at.isoformat.return_value = "2024-06-01T10:00:00"
    return log


# ── Flow 1: Register → Login ──────────────────────────────────────────────────

class TestAuthFlow:
    def test_register_then_login(self, client, mock_db):
        """Full sign-up → login cycle returns valid tokens."""
        new_user = _make_user(id=5, email="flow@example.com")

        with patch("app.services.auth_service.user_repo.create", return_value=new_user), \
             patch("app.services.auth_service.user_repo.get_by_email", return_value=new_user), \
             patch("app.services.auth_service.verify_password", return_value=True):

            signup_r = client.post("/auth/signup", json={
                "email": "flow@example.com", "password": "password123"
            })
            assert signup_r.status_code == 200
            signup_token = signup_r.json()["access_token"]
            assert signup_token

            login_r = client.post("/auth/login", json={
                "email": "flow@example.com", "password": "password123"
            })
            assert login_r.status_code == 200
            login_token = login_r.json()["access_token"]
            assert login_token

    def test_login_with_bad_password_then_good_password(self, client, mock_db):
        """Wrong password → 401; correct password → 200."""
        user = _make_user()

        with patch("app.services.auth_service.user_repo.get_by_email", return_value=user), \
             patch("app.services.auth_service.verify_password", return_value=False):
            r = client.post("/auth/login", json={"email": "u@x.com", "password": "wrong"})
        assert r.status_code == 401

        with patch("app.services.auth_service.user_repo.get_by_email", return_value=user), \
             patch("app.services.auth_service.verify_password", return_value=True):
            r = client.post("/auth/login", json={"email": "u@x.com", "password": "correct"})
        assert r.status_code == 200


# ── Flow 2: Login → Query (privacy gate) → History ───────────────────────────

class TestQueryAndHistoryFlow:
    def _auth_headers(self, user_id=1, role="user"):
        from app.core.security import create_access_token
        token = create_access_token(subject=str(user_id), role=role)
        return {"Authorization": f"Bearer {token}"}

    def test_query_blocked_then_visible_in_history(self, client, mock_db):
        """A blocked (privacy-gated) query should still be logged and visible in history."""
        user = _make_user(id=1)
        log = _make_log(user_id=1, question="What?", course_code="COMP0001", term="2024")
        log.status = "insufficient_evidence"
        log.result_count = 0

        mock_db.query.return_value.filter.return_value.first.return_value = user

        headers = self._auth_headers(user_id=1)

        # Step 1: submit query that hits privacy gate
        with patch("app.routers.insights.feedback_repo.count_by_filter", return_value=3), \
             patch("app.repositories.query_log_repo.query_log_repo.create", return_value=log):
            q_r = client.post("/query", json={
                "program": "COMP0001", "year": "2024", "question": "What?"
            }, headers=headers)
        assert q_r.json()["blocked_by_privacy"] is True

        # Step 2: verify query appears in history
        with patch("app.routers.history.query_log_repo.get_by_user", return_value=[log]):
            h_r = client.get("/history", headers=headers)
        assert h_r.status_code == 200
        assert len(h_r.json()) == 1
        assert h_r.json()[0]["status"] == "insufficient_evidence"

    def test_unauthenticated_cannot_access_history(self, client, mock_db):
        r = client.get("/history")
        assert r.status_code in (401, 403)

    def test_unauthenticated_cannot_query(self, client, mock_db):
        r = client.post("/query", json={
            "program": "CS", "year": "2024", "question": "Any?"
        })
        assert r.status_code in (401, 403)


# ── Flow 3: Admin user management flow ───────────────────────────────────────

class TestAdminFlow:
    def _admin_headers(self, admin_id=1):
        from app.core.security import create_access_token
        token = create_access_token(subject=str(admin_id), role="admin")
        return {"Authorization": f"Bearer {token}"}

    def test_admin_lists_and_deletes_user(self, client, mock_db):
        """Admin fetches user list then deletes a user."""
        admin = _make_user(id=1, email="admin@example.com", role="admin")
        regular = _make_user(id=2, email="user@example.com", role="user")
        mock_db.query.return_value.filter.return_value.first.return_value = admin
        headers = self._admin_headers(admin_id=1)

        with patch("app.routers.admin.user_repo.get_all", return_value=[admin, regular]):
            list_r = client.get("/admin/users", headers=headers)
        assert list_r.status_code == 200
        assert len(list_r.json()) == 2

        with patch("app.routers.admin.user_repo.delete"):
            del_r = client.delete("/admin/users/2", headers=headers)
        assert del_r.status_code == 200

    def test_regular_user_cannot_access_admin_endpoints(self, client, mock_db):
        """A user-role token must be rejected on all admin routes."""
        user = _make_user(id=2, role="user")
        mock_db.query.return_value.filter.return_value.first.return_value = user
        from app.core.security import create_access_token
        token = create_access_token(subject="2", role="user")
        headers = {"Authorization": f"Bearer {token}"}

        assert client.get("/admin/users", headers=headers).status_code == 403
        assert client.get("/admin/analytics", headers=headers).status_code == 403
        assert client.get("/admin/logs", headers=headers).status_code == 403


# ── Flow 4: Token edge cases ──────────────────────────────────────────────────

class TestTokenEdgeCases:
    def test_expired_token_rejected(self, client, mock_db):
        """A token with a past expiry must be rejected."""
        from datetime import timedelta
        from app.core.security import create_access_token
        token = create_access_token(subject="1", role="user",
                                    expires_delta=timedelta(seconds=-1))
        headers = {"Authorization": f"Bearer {token}"}
        r = client.post("/query", json={"program": "CS", "year": "2024", "question": "?"}, headers=headers)
        assert r.status_code in (401, 403)

    def test_malformed_token_rejected(self, client, mock_db):
        headers = {"Authorization": "Bearer this.is.garbage"}
        r = client.get("/history", headers=headers)
        assert r.status_code in (401, 403)

    def test_missing_bearer_prefix_rejected(self, client, mock_db):
        from app.core.security import create_access_token
        token = create_access_token(subject="1", role="user")
        headers = {"Authorization": token}  # missing "Bearer "
        r = client.get("/history", headers=headers)
        assert r.status_code in (401, 403)
