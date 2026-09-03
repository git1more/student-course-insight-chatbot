from dataclasses import dataclass
from datetime import datetime

@dataclass
class QueryLog:
    id: int
    user_id: int
    course_code: str
    term: str
    question: str
    duration_ms: int
    result_count: int
    status: str
    created_at: datetime
