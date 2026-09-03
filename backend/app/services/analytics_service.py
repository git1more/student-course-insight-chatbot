from sqlalchemy.orm import Session
from app.repositories.query_log_repo import query_log_repo


class AnalyticsService:
    def get_admin_analytics(self, db: Session):
        return {
            'total_queries': query_log_repo.total_queries(db),
            'ok_queries': query_log_repo.ok_queries(db),
            'blocked_queries': query_log_repo.blocked_queries(db),
            'avg_duration_ms': query_log_repo.avg_duration_ms(db),
            'most_queried_courses': query_log_repo.most_queried_courses(db),
            'status_breakdown': query_log_repo.status_breakdown(db),
        }


analytics_service = AnalyticsService()
