"""
Retrieval-Augmented Generation (RAG) retrieval layer.

This service handles the retrieval step of the RAG pipeline:

1. Embed the user's question using :class:`~app.services.embedding_service.EmbeddingService`.
2. Run a pgvector cosine-similarity search against ``feedback_comments`` rows
   that have stored embeddings.
3. Fall back to unranked results (first *top_k* rows) when no embeddings are
   stored yet (e.g. during initial data ingestion).

The retrieved comments are then passed to
:class:`~app.services.llm_service.LLMService` for structured analysis.
"""
from sqlalchemy.orm import Session
from app.db.models import FeedbackComment
from app.repositories.feedback_repo import feedback_repo
from app.services.embedding_service import embedding_service


class RAGService:
    """Retrieves the most relevant feedback comments for a user query."""

    def retrieve(
        self,
        db: Session,
        program: str,
        year: str | None,
        question: str,
        top_k: int = 5,
    ) -> list[FeedbackComment]:
        """Return the *top_k* feedback comments most relevant to *question*.

        Uses OpenAI's ``text-embedding-3-small`` to embed the question and
        then queries pgvector for the nearest neighbours within the specified
        programme/year scope.

        Args:
            db:       Active database session.
            program:  Programme code filter (case-insensitive).
            year:     Academic term filter; ``None`` means all years.
            question: The user's natural-language query.
            top_k:    Maximum number of comments to retrieve.

        Returns:
            A list of :class:`FeedbackComment` instances ordered by
            cosine similarity (most relevant first), or the first *top_k*
            unranked results if no embeddings exist.
        """
        # Step 1 — embed the question to get a query vector
        query_embedding = embedding_service.embed_text(question)

        # Step 2 — cosine similarity search via pgvector
        results = feedback_repo.search_similar(db, program, year, query_embedding, top_k)

        # Step 3 — fallback to unranked if no embeddings stored yet
        if not results:
            results = feedback_repo.get_all_by_filter(db, program, year)[:top_k]

        return results


# Module-level singleton — import this instance rather than the class.
rag_service = RAGService()
