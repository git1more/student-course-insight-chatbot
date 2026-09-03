"""
Repository for the ``query_logs`` table.

Each row records one insight query: who ran it, what they asked, how long it
took, and the full JSON response.  Analytics methods derived from this table
power the admin dashboard.
"""
from collections import Counter
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import QueryLog


class QueryLogRepository:
    """Data-access object for :class:`~app.db.models.QueryLog`."""

    def create(
        self,
        db: Session,
        user_id: int,
        course_code: str,
        term: str,
        question: str,
        duration_ms: int,
        result_count: int,
        status: str,
        result_json: str | None = None,
    ) -> QueryLog:
        """Persist a new query log entry and return it.

        Called at the end of every ``POST /query`` request (both successful and
        privacy-blocked) so that the full audit trail is maintained.

        Args:
            db:           Active database session.
            user_id:      Foreign key to ``users.id``.
            course_code:  Programme queried (e.g. ``"COMP9900"``).
            term:         Academic term filter used (empty string if none).
            question:     The user's natural-language question.
            duration_ms:  Wall-clock pipeline duration in milliseconds.
            result_count: Number of evidence items returned (0 if blocked).
            status:       ``"ok"`` or ``"insufficient_evidence"``.
            result_json:  Serialised :class:`InsightResponse` JSON for history replay.

        Returns:
            The newly created :class:`QueryLog` ORM instance.
        """
        log = QueryLog(
            user_id=user_id,
            course_code=course_code,
            term=term,
            question=question,
            duration_ms=duration_ms,
            result_count=result_count,
            status=status,
            result_json=result_json,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def get_by_user(self, db: Session, user_id: int) -> list[QueryLog]:
        """Return all logs for a specific user, newest first.

        Used by ``GET /history`` to populate the user's query history page.
        """
        return (
            db.query(QueryLog)
            .filter(QueryLog.user_id == user_id)
            .order_by(QueryLog.created_at.desc())
            .all()
        )

    def get_all(self, db: Session) -> list[QueryLog]:
        """Return every query log across all users, newest first.

        Used by ``GET /admin/logs`` for the admin audit view.
        """
        return db.query(QueryLog).order_by(QueryLog.created_at.desc()).all()

    # ── Analytics helpers (used by AnalyticsService / admin dashboard) ────────

    def total_queries(self, db: Session) -> int:
        """Total number of queries ever submitted."""
        return db.query(QueryLog).count()

    def ok_queries(self, db: Session) -> int:
        """Number of queries that completed successfully (status == ``"ok"``)."""
        return db.query(QueryLog).filter(QueryLog.status == 'ok').count()

    def blocked_queries(self, db: Session) -> int:
        """Number of queries blocked by the privacy gate."""
        return db.query(QueryLog).filter(QueryLog.status == 'insufficient_evidence').count()

    def most_queried_courses(self, db: Session) -> list[dict]:
        """Return the top-5 most frequently queried course codes.

        Returns:
            A list of ``{"course_code": str, "count": int}`` dicts, sorted by count descending.
        """
        rows = db.query(QueryLog.course_code).all()
        counter = Counter(r.course_code for r in rows)
        return [{'course_code': k, 'count': v} for k, v in counter.most_common(5)]

    def status_breakdown(self, db: Session) -> list[dict]:
        """Return query counts grouped by status value.

        Returns:
            A list of ``{"status": str, "count": int}`` dicts.
        """
        rows = db.query(QueryLog.status).all()
        counter = Counter(r.status for r in rows)
        return [{'status': k, 'count': v} for k, v in counter.items()]

    def avg_duration_ms(self, db: Session) -> float:
        """Return the mean query pipeline duration across all logs, in milliseconds."""
        result = db.query(func.avg(QueryLog.duration_ms)).scalar()
        return round(float(result), 2) if result else 0.0


# Module-level singleton — import this instance rather than the class.
query_log_repo = QueryLogRepository()
