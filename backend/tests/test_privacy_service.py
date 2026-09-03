"""
Unit tests — app/services/privacy_service.py

Covers: confidence band calculation (pure function) and the privacy sample-size
gate (mocks feedback_repo so no DB needed).
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.privacy_service import PrivacyService


@pytest.fixture
def svc():
    return PrivacyService()


def _fake_comments(n: int):
    return [MagicMock() for _ in range(n)]


# ── compute_confidence (pure) ─────────────────────────────────────────────────

class TestComputeConfidence:
    def test_high_above_threshold(self, svc):
        assert svc.compute_confidence(25, 6) == "High"

    def test_high_at_boundary(self, svc):
        assert svc.compute_confidence(20, 5) == "High"

    def test_medium_above_threshold(self, svc):
        assert svc.compute_confidence(15, 4) == "Medium"

    def test_medium_at_boundary(self, svc):
        assert svc.compute_confidence(10, 3) == "Medium"

    def test_low_small_sample(self, svc):
        assert svc.compute_confidence(5, 2) == "Low"

    def test_low_zero_values(self, svc):
        assert svc.compute_confidence(0, 0) == "Low"

    def test_low_when_evidence_too_small(self, svc):
        """Large sample but evidence below threshold → Low."""
        assert svc.compute_confidence(50, 1) == "Low"

    def test_low_when_sample_too_small(self, svc):
        """Enough evidence but sample below threshold → Low."""
        assert svc.compute_confidence(9, 6) == "Low"


# ── check_sample_size (mocked repo) ──────────────────────────────────────────

class TestCheckSampleSize:
    """
    check_sample_size delegates to feedback_repo.get_by_course_term.
    We mock that method and pass a dummy db session.
    """

    def _patch(self, n):
        return patch(
            "app.services.privacy_service.feedback_repo.get_by_course_term",
            return_value=_fake_comments(n),
        )

    def _db(self):
        from unittest.mock import MagicMock
        return MagicMock()

    def test_passes_above_threshold(self, svc):
        with self._patch(15):
            passed, count = svc.check_sample_size(self._db(), "COMP9900", "2024")
        assert passed is True
        assert count == 15

    def test_blocked_below_threshold(self, svc):
        with self._patch(5):
            passed, count = svc.check_sample_size(self._db(), "COMP9900", "2024")
        assert passed is False
        assert count == 5

    def test_blocked_at_nine(self, svc):
        with self._patch(9):
            passed, count = svc.check_sample_size(self._db(), "COMP1511", "2023")
        assert passed is False

    def test_passes_at_exactly_ten(self, svc):
        with self._patch(10):
            passed, count = svc.check_sample_size(self._db(), "COMP1511", "2023")
        assert passed is True

    def test_empty_result_blocked(self, svc):
        with self._patch(0):
            passed, count = svc.check_sample_size(self._db(), "NONEXISTENT", "2099")
        assert passed is False
        assert count == 0
