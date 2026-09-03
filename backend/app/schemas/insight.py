from pydantic import BaseModel


class InsightQueryRequest(BaseModel):
    program: str
    year: str | None = None
    question: str


class EvidenceItem(BaseModel):
    comment_id: str
    excerpt: str


class RankedTheme(BaseModel):
    theme: str
    volume: str    # High | Medium | Low
    recency: str   # Recent | Stable | Declining


class RecommendedAction(BaseModel):
    action: str
    owner: str     # e.g. "Course Coordinator", "Teaching Team"
    effort: str    # Low | Medium | High
    impact: str    # Low | Medium | High


class TypicalityPanel(BaseModel):
    sample_size: int
    timeframe: str | None = None
    confidence: str              # High | Medium | Low
    limitations: str = ''
    contradiction_detected: bool = False


class InsightResponse(BaseModel):
    # Part 1 — Executive summary
    executive_summary: str
    # Part 2 — Ranked themes/issues
    ranked_themes: list[RankedTheme]
    # Part 3 — Evidence excerpts (populated by the router, not the LLM)
    supporting_evidence: list[EvidenceItem]
    # Part 4 — Interpretation
    interpretation: str
    # Part 5 — Recommended actions
    recommended_actions: list[RecommendedAction]
    # Part 6 — Confidence + caveats
    typicality: TypicalityPanel
    # Extra
    follow_up_questions: list[str]
    message: str = ''
    blocked_by_privacy: bool = False
