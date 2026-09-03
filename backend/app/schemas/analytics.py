from pydantic import BaseModel

class AdminAnalyticsResponse(BaseModel):
    total_queries: int
    most_queried_courses: list[dict]
    status_breakdown: list[dict]
