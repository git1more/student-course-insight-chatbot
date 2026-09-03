"""
SQLAlchemy ORM models for the Student Course Insight Chatbot.

Three tables are defined:
- ``users``             — authenticated users (staff / admin)
- ``feedback_comments`` — anonymised student feedback with pgvector embeddings
- ``query_logs``        — history of insight queries made by users
"""
from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base
from app.core.config import settings


class User(Base):
    """Represents a system user (academic staff or administrator).

    Roles:
        ``user``  — can run queries and view their own history.
        ``admin`` — additionally manages users and views all analytics.
    """
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default='user')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ``passive_deletes=True`` tells SQLAlchemy NOT to load or nullify child rows
    # before deletion — the database handles cascading via the FK constraint
    # (``ON DELETE CASCADE`` set in migration 003_fix_cascade_delete).
    query_logs: Mapped[list['QueryLog']] = relationship('QueryLog', back_populates='user', passive_deletes=True)


class FeedbackComment(Base):
    """Stores a single anonymised student feedback comment.

    The ``embedding`` column holds a 1536-dimensional vector (text-embedding-3-small)
    used for cosine similarity retrieval via pgvector.  Comments without an
    embedding are excluded from semantic search but can still appear via the
    keyword fallback.
    """
    __tablename__ = 'feedback_comments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Unique identifier from the original Excel dataset (preserves idempotent ingest)
    comment_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    # Course code / programme name (e.g. "COMP9900")
    program: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Academic term / year string (e.g. "24T3")
    year: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    # OpenAI embedding vector (nullable — rows without embeddings skip semantic search)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dimensions), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class QueryLog(Base):
    """Audit record for every insight query submitted by a user.

    Stores the full JSON response so that history entries can be replayed
    without hitting OpenAI again.  The ``status`` column distinguishes
    successful queries (``ok``) from those blocked by the privacy gate
    (``insufficient_evidence``).
    """
    __tablename__ = 'query_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # FK to users.id — cascades on delete so removing a user cleans up their logs
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text)
    course_code: Mapped[str] = mapped_column(String(255))
    term: Mapped[str] = mapped_column(String(50))
    # Wall-clock time for the full query pipeline in milliseconds
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    # Number of evidence snippets returned (0 when privacy-blocked)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    # ``ok`` | ``insufficient_evidence``
    status: Mapped[str] = mapped_column(String(50), default='success')
    # Full serialised InsightResponse JSON — enables one-click history replay
    result_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped['User'] = relationship('User', back_populates='query_logs')
