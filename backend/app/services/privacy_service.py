"""
Privacy gate and confidence-band logic.

The privacy gate enforces a minimum sample-size rule: if fewer than
``settings.privacy_min_sample_size`` (default 10) comments match a given
course/term filter, the query is blocked and no LLM call is made.  This
prevents de-anonymisation of students when feedback volumes are very small.

Confidence bands are derived from both total sample size and the number of
semantically relevant evidence items retrieved, giving academic staff a
qualitative signal about result reliability.
"""
from sqlalchemy.orm import Session
from app.core.config import settings
from app.repositories.feedback_repo import feedback_repo


class PrivacyService:
    """Stateless service for privacy gating and confidence scoring."""

    def check_sample_size(self, db: Session, course_code: str, term: str) -> tuple[bool, int]:
        """Determine whether a query has sufficient evidence to proceed.

        Fetches all comments matching ``course_code`` and ``term``, then
        compares the count against the configured minimum sample size.

        Args:
            db:          Active database session.
            course_code: Programme code to filter on (e.g. ``"COMP9900"``).
            term:        Academic term string (e.g. ``"24T3"``), or empty/None for all terms.

        Returns:
            A ``(passes, n)`` tuple where *passes* is ``True`` when the comment
            count meets the threshold, and *n* is the raw count.
        """
        comments = feedback_repo.get_by_course_term(db, course_code=course_code, term=term)
        n = len(comments)
        return n >= settings.privacy_min_sample_size, n

    def compute_confidence(self, sample_size: int, evidence_count: int) -> str:
        """Derive a qualitative confidence label from sample and evidence counts.

        Confidence tiers:
            ``"High"``   — ≥ 20 total comments and ≥ 5 evidence items retrieved.
            ``"Medium"`` — ≥ 10 total comments and ≥ 3 evidence items retrieved.
            ``"Low"``    — anything below the Medium thresholds.

        Args:
            sample_size:    Total comments matching the course/term filter.
            evidence_count: Number of semantically relevant comments retrieved by RAG.

        Returns:
            One of ``"High"``, ``"Medium"``, or ``"Low"``.
        """
        if sample_size >= 20 and evidence_count >= 5:
            return 'High'
        if sample_size >= 10 and evidence_count >= 3:
            return 'Medium'
        return 'Low'


# Module-level singleton — import this instance rather than the class.
privacy_service = PrivacyService()
