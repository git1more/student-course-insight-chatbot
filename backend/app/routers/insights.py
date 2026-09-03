"""
Insight query router — the core RAG + LLM pipeline endpoint.

Endpoints:
    GET  /insights/programs  — list all distinct programme codes
    GET  /insights/years     — list all distinct term/year strings
    POST /query              — run a natural-language insight query

The ``POST /query`` endpoint implements the full pipeline:

    1. **Privacy gate**  — block queries with fewer than 10 matching comments.
    2. **Semantic retrieval** — embed the question and retrieve top-K comments
       via pgvector cosine similarity (RAG).
    3. **Structured LLM response** — pass retrieved comments to GPT-4o-mini,
       requesting a six-part academic insight report as structured JSON.
    4. **Log** — persist the full request and response for history and analytics.

All endpoints require a valid Bearer JWT (``get_current_user`` dependency).
"""
import json
import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.base import get_db
from app.repositories.feedback_repo import feedback_repo
from app.repositories.query_log_repo import query_log_repo
from app.schemas.insight import (
    InsightQueryRequest,
    InsightResponse,
    EvidenceItem,
    RankedTheme,
    RecommendedAction,
    TypicalityPanel,
)
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service

router = APIRouter(tags=['insights'])

# Number of evidence comments to retrieve from pgvector and send to the LLM
TOP_K = 5


def _compute_confidence(n: int) -> str:
    """Map total comment count to a qualitative confidence label.

    Thresholds:
        n ≥ 30  → ``"High"``
        n ≥ 15  → ``"Medium"``
        n < 15  → ``"Low"``
    """
    if n >= 30:
        return 'High'
    if n >= 15:
        return 'Medium'
    return 'Low'


@router.get('/insights/programs')
def get_programs(db: Session = Depends(get_db)):
    """Return the list of all programme codes available in the database.

    Used to populate the course-code dropdown in the frontend query form.
    No authentication required — data is not sensitive.
    """
    return {'programs': feedback_repo.get_programs(db)}


@router.get('/insights/years')
def get_years(db: Session = Depends(get_db)):
    """Return the list of all academic term/year strings in the database.

    Used to populate the term dropdown in the frontend query form.
    """
    return {'years': feedback_repo.get_years(db)}


@router.post('/query', response_model=InsightResponse)
def query_insight(
    payload: InsightQueryRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Run a natural-language insight query against the feedback dataset.

    Pipeline steps (see module docstring for details):
        1. Privacy gate — return a blocked response if n < 10.
        2. Semantic retrieval — top-K comments via pgvector.
        3. Structured LLM response — six-part academic report from GPT-4o-mini.
        4. Query log — persists request metadata and JSON response.

    Args:
        payload:      Validated request body (programme, year, question).
        db:           Injected database session.
        current_user: Authenticated user resolved from the Bearer JWT.

    Returns:
        :class:`InsightResponse` — six-part structured report, or a privacy-blocked stub.
    """
    start = time.perf_counter()
    program = payload.program.strip()
    year = payload.year.strip() if payload.year else None

    # ── Step 1: Privacy gate ──────────────────────────────────────────────────
    # Count comments matching the filter before touching the LLM.
    n = feedback_repo.count_by_filter(db, program, year)

    if n < 10:
        # Block the query and log it — the frontend shows an informative message.
        duration_ms = int((time.perf_counter() - start) * 1000)
        blocked_response = InsightResponse(
            message=(
                f'There are not enough comments (n={n}) for this filter. '
                'Please broaden the program or year selection. At least 10 are required.'
            ),
            executive_summary='Insufficient evidence — privacy gate active.',
            ranked_themes=[],
            supporting_evidence=[],
            interpretation='',
            recommended_actions=[],
            typicality=TypicalityPanel(
                sample_size=n, timeframe=year, confidence='Low',
                limitations='Sample size below privacy threshold of 10.',
            ),
            follow_up_questions=[],
            blocked_by_privacy=True,
        )
        query_log_repo.create(
            db,
            user_id=current_user.id,
            course_code=program,
            term=year or '',
            question=payload.question,
            duration_ms=duration_ms,
            result_count=0,
            status='insufficient_evidence',
            result_json=blocked_response.model_dump_json(),
        )
        return blocked_response

    # ── Step 2: Semantic retrieval (RAG) ──────────────────────────────────────
    # Embed the question and retrieve the top-K most relevant comments.
    retrieved = rag_service.retrieve(db, program, year, payload.question, top_k=TOP_K)

    # ── Step 3: Structured LLM response ──────────────────────────────────────
    # Send retrieved comments to GPT-4o-mini and request a six-part JSON report.
    llm_data = llm_service.generate_structured_response(
        program=program,
        year=year,
        question=payload.question,
        comments=retrieved,
        sample_size=n,
    )

    # Build evidence list from retrieved comments (Part 3 of the report).
    # Excerpts are truncated to 300 characters to keep the payload manageable.
    supporting_evidence = [
        EvidenceItem(comment_id=str(c.comment_id), excerpt=c.comment_text[:300])
        for c in retrieved
    ]

    confidence = _compute_confidence(n)

    # Assemble the full InsightResponse from LLM output and local metadata
    response = InsightResponse(
        message='Evidence retrieved and analysed successfully.',
        executive_summary=llm_data['executive_summary'],
        ranked_themes=[
            RankedTheme(
                theme=t['theme'],
                volume=t.get('volume', 'Low'),
                recency=t.get('recency', 'Stable'),
            )
            for t in llm_data['ranked_themes']
        ],
        supporting_evidence=supporting_evidence,
        interpretation=llm_data['interpretation'],
        recommended_actions=[
            RecommendedAction(
                action=a['action'],
                owner=a.get('owner', 'Course Coordinator'),
                effort=a.get('effort', 'Medium'),
                impact=a.get('impact', 'Medium'),
            )
            for a in llm_data['recommended_actions']
        ],
        typicality=TypicalityPanel(
            sample_size=n,
            timeframe=year or 'All years',
            confidence=confidence,
            limitations=llm_data.get('limitations', ''),
            contradiction_detected=llm_data.get('contradiction_detected', False),
        ),
        follow_up_questions=llm_data['follow_up_questions'],
        blocked_by_privacy=False,
    )

    # ── Step 4: Audit log ─────────────────────────────────────────────────────
    duration_ms = int((time.perf_counter() - start) * 1000)
    query_log_repo.create(
        db,
        user_id=current_user.id,
        course_code=program,
        term=year or '',
        question=payload.question,
        duration_ms=duration_ms,
        result_count=len(supporting_evidence),
        status='ok',
        result_json=response.model_dump_json(),  # stored for history replay
    )

    return response
