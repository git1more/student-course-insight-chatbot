from dataclasses import dataclass
from datetime import date

@dataclass
class FeedbackComment:
    id: int
    course_code: str
    term: str
    comment_text: str
    sentiment: str
    created_at: date
