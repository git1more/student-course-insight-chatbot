"""
Unit tests — app/routers/auth.py

Uses TestClient with auth_service mocked.
Covers: happy paths, validation errors, duplicate email, bad credentials.
"""
import pytest
from unittest.mock import patch


class TestSignupEndpoint:
    def test_success_200(self, client):
        with patch("app.routers.auth.auth_service.signup",
                   return_value={"access_token": "tok", "role": "user"}):
            r = client.post("/auth/signup", json={
                "email": "new@example.com", "password": "password123", "role": "user"
            })
        assert r.status_code == 200
        assert r.json()["access_token"] == "tok"
        assert r.json()["role"] == "user"

    def test_duplicate_email_400(self, client):
        with patch("app.routers.auth.auth_service.signup",
                   side_effect=ValueError("Email already registered")):
            r = client.post("/auth/signup", json={
                "email": "dup@example.com", "password": "password123"
            })
        assert r.status_code == 400
        assert "already registered" in r.json()["detail"]

    def test_missing_email_422(self, client):
        r = client.post("/auth/signup", json={"password": "password123"})
        assert r.status_code == 422

    def test_missing_password_422(self, client):
        r = client.post("/auth/signup", json={"email": "a@b.com"})
        assert r.status_code == 422

    def test_invalid_email_format_422(self, client):
        r = client.post("/auth/signup", json={"email": "not-email", "password": "pass123"})
        assert r.status_code == 422

    def test_password_below_min_length_rejected(self, client):
        """Schema enforces min_length=6; passwords shorter than 6 chars return 422."""
        r = client.post("/auth/signup", json={"email": "a@b.com", "password": "abc"})
        assert r.status_code == 422

    def test_password_at_min_length_accepted(self, client):
        """Password of exactly 6 characters passes schema validation."""
        with patch("app.routers.auth.auth_service.signup",
                   return_value={"access_token": "tok", "role": "user"}):
            r = client.post("/auth/signup", json={"email": "a@b.com", "password": "abc123"})
        assert r.status_code == 200


class TestLoginEndpoint:
    def test_success_200(self, client):
        with patch("app.routers.auth.auth_service.login",
                   return_value={"access_token": "jwt", "role": "admin"}):
            r = client.post("/auth/login", json={
                "email": "admin@example.com", "password": "password123"
            })
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_wrong_credentials_401(self, client):
        with patch("app.routers.auth.auth_service.login",
                   side_effect=ValueError("Invalid email or password")):
            r = client.post("/auth/login", json={
                "email": "u@x.com", "password": "wrong"
            })
        assert r.status_code == 401
        assert "Invalid" in r.json()["detail"]

    def test_missing_email_422(self, client):
        r = client.post("/auth/login", json={"password": "pass"})
        assert r.status_code == 422

    def test_missing_password_422(self, client):
        r = client.post("/auth/login", json={"email": "a@b.com"})
        assert r.status_code == 422


class TestLogoutEndpoint:
    def test_logout_200(self, client):
        r = client.post("/auth/logout")
        assert r.status_code == 200
        assert r.json()["message"] == "Logged out successfully"

    def test_logout_needs_no_token(self, client):
        """Stateless logout — no Authorization header required."""
        r = client.post("/auth/logout")
        assert r.status_code == 200


class TestHealthEndpoints:
    def test_root_200(self, client):
        assert client.get("/").status_code == 200

    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
