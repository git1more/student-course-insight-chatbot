"""
Repository for the ``feedback_comments`` table.

Provides upsert-based data ingestion, course/term metadata queries,
cosine-similarity vector search (via pgvector), and plain filtered retrieval.

All public methods accept a SQLAlchemy ``Session`` as their first argument so
they remain testable with mock sessions (no real database required in tests).
"""
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import FeedbackComment


# ── Private filter helpers ────────────────────────────────────────────────────

def _program_filter(q, program: str):
    """Apply a case-insensitive equality filter on the ``program`` column."""
    return q.filter(func.lower(FeedbackComment.program) == program.lower().strip())


def _year_filter(q, year: str | None):
    """Optionally filter by ``year``; returns the query unchanged when *year* is blank."""
    if year and year.strip():
        return q.filter(FeedbackComment.year == year.strip())
    return q


# ── Repository class ──────────────────────────────────────────────────────────

class FeedbackRepository:
    """Data-access object for :class:`~app.db.models.FeedbackComment`."""

    def upsert(
        self,
        db: Session,
        comment_id: str,
        program: str,
        year: str,
        comment_text: str,
        embedding: list[float] | None = None,
    ) -> FeedbackComment:
        """Insert a new comment or update an existing one (keyed on *comment_id*).

        This is called during the Excel ingestion pipeline to ensure the
        operation is idempotent — re-ingesting the same file won't create
        duplicate rows.

        Args:
            db:           Active database session.
            comment_id:   Unique identifier from the source dataset.
            program:      Course/programme code (e.g. ``"COMP9900"``).
            year:         Academic term string (e.g. ``"24T3"``).
            comment_text: Raw student feedback text.
            embedding:    Pre-computed OpenAI embedding vector, or ``None`` if
                          the embedding step was skipped.

        Returns:
            The inserted or updated :class:`FeedbackComment` ORM instance.
        """
        existing = db.query(FeedbackComment).filter(FeedbackComment.comment_id == comment_id).first()
        if existing:
            # Update all mutable fields on re-ingest
            existing.program = program
            existing.year = year
            existing.comment_text = comment_text
            if embedding is not None:
                existing.embedding = embedding
            db.commit()
            db.refresh(existing)
            return existing

        # New comment — create and persist
        comment = FeedbackComment(
            comment_id=comment_id,
            program=program,
            year=year,
            comment_text=comment_text,
            embedding=embedding,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    def get_programs(self, db: Session) -> list[str]:
        """Return a sorted list of all distinct programme codes in the database."""
        rows = db.query(FeedbackComment.program).distinct().order_by(FeedbackComment.program).all()
        return [r.program for r in rows]

    def get_years(self, db: Session) -> list[str]:
        """Return a sorted list of all distinct year/term strings in the database."""
        rows = db.query(FeedbackComment.year).distinct().order_by(FeedbackComment.year).all()
        return [r.year for r in rows]

    def count_by_filter(self, db: Session, program: str, year: str | None = None) -> int:
        """Count comments matching the given programme and optional year.

        Used by the privacy gate to decide whether a query has enough evidence
        (at least 10 comments) before calling the LLM.
        """
        q = _program_filter(db.query(FeedbackComment), program)
        q = _year_filter(q, year)
        return q.count()

    def search_similar(
        self,
        db: Session,
        program: str,
        year: str | None,
        query_embedding: list[float],
        top_k: int = 6,
    ) -> list[FeedbackComment]:
        """Retrieve the *top_k* comments most similar to *query_embedding*.

        Uses pgvector's ``<=>`` cosine distance operator, ordering results from
        most to least relevant.  Only rows with a stored embedding are considered.

        Args:
            db:              Active database session.
            program:         Programme code filter (case-insensitive).
            year:            Term filter (optional).
            query_embedding: Embedding of the user's question.
            top_k:           Maximum number of results to return.

        Returns:
            A list of :class:`FeedbackComment` instances ordered by similarity.
        """
        q = _program_filter(
            db.query(FeedbackComment).filter(FeedbackComment.embedding.isnot(None)),
            program,
        )
        q = _year_filter(q, year)
        return q.order_by(FeedbackComment.embedding.cosine_distance(query_embedding)).limit(top_k).all()

    def get_all_by_filter(self, db: Session, program: str, year: str | None = None) -> list[FeedbackComment]:
        """Return all comments matching the programme and optional year filter.

        Used as a keyword-search fallback when no embeddings are stored, and
        also by the privacy service to count raw comment volume.
        """
        q = _program_filter(db.query(FeedbackComment), program)
        q = _year_filter(q, year)
        return q.all()

    def get_by_course_term(self, db: Session, course_code: str, term: str | None = None) -> list[FeedbackComment]:
        """Retrieve all comments for a given course code and optional term.

        Thin alias over :meth:`get_all_by_filter` used by the privacy service,
        which refers to the course code using the ``course_code`` parameter name.
        """
        return self.get_all_by_filter(db, program=course_code, year=term)


# Module-level singleton — import this instance rather than the class.
feedback_repo = FeedbackRepository()
