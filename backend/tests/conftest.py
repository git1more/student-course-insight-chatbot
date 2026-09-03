"""
Shared pytest fixtures.

Patches init_db and SessionLocal so tests never connect to a real PostgreSQL.
The get_db dependency is overridden per-test with a MagicMock session.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def patch_db_startup():
    """Stop the lifespan from connecting to PostgreSQL during the test run."""
    with patch("app.db.base.init_db", return_value=None), \
         patch("app.db.base.SessionLocal", return_value=MagicMock()), \
         patch("app.repositories.user_repo.user_repo.seed_demo_users", return_value=None), \
         patch("app.repositories.feedback_repo.feedback_repo.count_by_filter", return_value=1):
        yield


@pytest.fixture
def mock_db():
    """A fresh MagicMock standing in for a SQLAlchemy Session."""
    return MagicMock()


@pytest.fixture
def client(mock_db):
    """TestClient with get_db overridden — no real DB required."""
    from app.main import app
    from app.db.base import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def make_auth_header(subject: str = "1", role: str = "user") -> dict:
    """Return a Bearer-token Authorization header for the given subject/role."""
    from app.core.security import create_access_token
    token = create_access_token(subject=subject, role=role)
    return {"Authorization": f"Bearer {token}"}
