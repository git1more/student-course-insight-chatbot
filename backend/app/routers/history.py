import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.base import get_db
from app.repositories.query_log_repo import query_log_repo

router = APIRouter(prefix='/history', tags=['history'])


@router.get('')
def get_my_history(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    logs = query_log_repo.get_by_user(db, current_user.id)
    return [
        {
            'id': log.id,
            'question': log.question,
            'course_code': log.course_code,
            'term': log.term,
            'duration_ms': log.duration_ms,
            'result_count': log.result_count,
            'status': log.status,
            'created_at': log.created_at.isoformat(),
            'result': json.loads(log.result_json) if log.result_json else None,
        }
        for log in logs
    ]
