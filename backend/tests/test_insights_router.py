"""
Unit tests — app/routers/insights.py

Covers: privacy gate (n < 10), successful query flow, programs/years endpoints.
External services (RAG, LLM, embedding) are fully mocked.
"""
import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import make_auth_header


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_comment(comment_id="C001", text="Sample feedback text for testing purposes."):
    c = MagicMock()
    c.comment_id = comment_id
    c.comment_text = text
    return c


def _llm_response():
    return {
        "executive_summary": "Test summary.",
        "ranked_themes": [{"theme": "Workload", "volume": "High", "recency": "Recent"}],
        "interpretation": "Test interpretation.",
        "recommended_actions": [{"action": "Reduce load", "owner": "Coordinator",
                                  "effort": "Medium", "impact": "High"}],
        "limitations": "Dataset is improvement-only.",
        "contradiction_detected": False,
        "follow_up_questions": ["What about labs?"],
    }


def _user_db_lookup(mock_db, user_id=1, role="user"):
    """Make mock_db return a fake user when queried by id."""
    from app.db.models import User
    u = MagicMock(spec=User)
    u.id, u.role = user_id, role
    mock_db.query.return_value.filter.return_value.first.return_value = u
    return u


# ── GET /insights/programs ────────────────────────────────────────────────────

class TestGetPrograms:
    def test_returns_program_list(self, client, mock_db):
        with patch("app.routers.insights.feedback_repo.get_programs",
                   return_value=["Computer Science", "Engineering"]):
            r = client.get("/insights/programs")
        assert r.status_code == 200
        assert "Computer Science" in r.json()["programs"]

    def test_empty_list_when_no_data(self, client, mock_db):
        with patch("app.routers.insights.feedback_repo.get_programs", return_value=[]):
            r = client.get("/insights/programs")
        assert r.json()["programs"] == []


# ── GET /insights/years ───────────────────────────────────────────────────────

class TestGetYears:
    def test_returns_year_list(self, client, mock_db):
        with patch("app.routers.insights.feedback_repo.get_years",
                   return_value=["2023", "2024"]):
            r = client.get("/insights/years")
        assert "2024" in r.json()["years"]


# ── POST /query — privacy gate ────────────────────────────────────────────────

class TestPrivacyGate:
    def _post(self, client, mock_db, n_comments):
        _user_db_lookup(mock_db)
        headers = make_auth_header(subject="1", role="user")
        with patch("app.routers.insights.feedback_repo.count_by_filter", return_value=n_comments), \
             patch("app.repositories.query_log_repo.query_log_repo.create"):
            return client.post("/query", json={
                "program": "COMP9900", "year": "2024",
                "question": "What are the issues?"
            }, headers=headers)

    def test_blocked_when_fewer_than_10(self, client, mock_db):
        r = self._post(client, mock_db, 5)
        assert r.status_code == 200
        assert r.json()["blocked_by_privacy"] is True

    def test_blocked_at_zero(self, client, mock_db):
        r = self._post(client, mock_db, 0)
        assert r.json()["blocked_by_privacy"] is True

    def test_blocked_at_nine(self, client, mock_db):
        r = self._post(client, mock_db, 9)
        assert r.json()["blocked_by_privacy"] is True

    def test_not_blocked_at_ten(self, client, mock_db):
        _user_db_lookup(mock_db)
        headers = make_auth_header(subject="1", role="user")
        comments = [_fake_comment(f"C{i:03d}") for i in range(10)]
        with patch("app.routers.insights.feedback_repo.count_by_filter", return_value=10), \
             patch("app.routers.insights.rag_service.retrieve", return_value=comments), \
             patch("app.routers.insights.llm_service.generate_structured_response",
                   return_value=_llm_response()), \
             patch("app.repositories.query_log_repo.query_log_repo.create"):
            r = client.post("/query", json={
                "program": "COMP9900", "year": "2024",
                "question": "What are the issues?"
            }, headers=headers)
        assert r.status_code == 200
        assert r.json()["blocked_by_privacy"] is False

    def test_blocked_message_mentions_count(self, client, mock_db):
        r = self._post(client, mock_db, 3)
        assert "n=3" in r.json()["message"]


# ── POST /query — successful response ────────────────────────────────────────

class TestQuerySuccess:
    def test_response_has_six_parts(self, client, mock_db):
        _user_db_lookup(mock_db)
        headers = make_auth_header(subject="1", role="user")
        comments = [_fake_comment(f"C{i:03d}") for i in range(5)]
        with patch("app.routers.insights.feedback_repo.count_by_filter", return_value=15), \
             patch("app.routers.insights.rag_service.retrieve", return_value=comments), \
             patch("app.routers.insights.llm_service.generate_structured_response",
                   return_value=_llm_response()), \
             patch("app.repositories.query_log_repo.query_log_repo.create"):
            r = client.post("/query", json={
                "program": "Computer Science", "year": "2024",
                "question": "What are the issues?"
            }, headers=headers)
        data = r.json()
        assert r.status_code == 200
        assert "executive_summary" in data
        assert "ranked_themes" in data
        assert "supporting_evidence" in data
        assert "interpretation" in data
        assert "recommended_actions" in data
        assert "typicality" in data

    def test_evidence_has_comment_ids(self, client, mock_db):
        _user_db_lookup(mock_db)
        headers = make_auth_header(subject="1", role="user")
        comments = [_fake_comment("C001"), _fake_comment("C002")]
        with patch("app.routers.insights.feedback_repo.count_by_filter", return_value=20), \
             patch("app.routers.insights.rag_service.retrieve", return_value=comments), \
             patch("app.routers.insights.llm_service.generate_structured_response",
                   return_value=_llm_response()), \
             patch("app.repositories.query_log_repo.query_log_repo.create"):
            r = client.post("/query", json={
                "program": "CS", "year": "2024", "question": "What?"
            }, headers=headers)
        ids = [e["comment_id"] for e in r.json()["supporting_evidence"]]
        assert "C001" in ids
        assert "C002" in ids

    def test_unauthenticated_query_rejected(self, client, mock_db):
        """Request without Authorization header must be rejected."""
        r = client.post("/query", json={
            "program": "CS", "year": "2024", "question": "What?"
        })
        assert r.status_code in (401, 403)

    def test_missing_program_returns_422(self, client, mock_db):
        headers = make_auth_header()
        r = client.post("/query", json={"year": "2024", "question": "What?"}, headers=headers)
        assert r.status_code == 422
