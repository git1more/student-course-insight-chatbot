"""
Admin router — user management, analytics, query logs, and data ingestion.

All endpoints require the ``admin`` role (enforced by ``require_admin``).

Endpoints:
    GET    /admin/analytics              — aggregated dashboard metrics
    GET    /admin/users                  — list all registered users
    PATCH  /admin/users/{id}/role        — promote or demote a user
    GET    /admin/users/{id}/history     — view a specific user's query logs
    DELETE /admin/users/{id}             — permanently delete a user account
    GET    /admin/logs                   — all query logs across all users
    POST   /admin/ingest                 — re-run the Excel data ingestion pipeline

Guards:
    - An admin cannot change or delete their own account (self-lock prevention).
    - Role values are validated to ``"user"`` or ``"admin"`` only.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.base import get_db
from app.repositories.user_repo import user_repo
from app.repositories.query_log_repo import query_log_repo
from app.services.analytics_service import analytics_service

router = APIRouter(prefix='/admin', tags=['admin'])


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get('/analytics')
def get_admin_analytics(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """Return aggregated statistics for the admin dashboard.

    Metrics include total users, total/blocked/ok query counts, top-5 courses,
    status breakdown, and average query duration.
    """
    return analytics_service.get_admin_analytics(db)


# ── User management ───────────────────────────────────────────────────────────

@router.get('/users')
def list_users(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """Return a list of all registered user accounts.

    Returns:
        List of ``{id, email, role, created_at}`` dicts, ordered by database ID.
    """
    users = user_repo.get_all(db)
    return [
        {'id': u.id, 'email': u.email, 'role': u.role, 'created_at': u.created_at.isoformat()}
        for u in users
    ]


class RoleUpdate(BaseModel):
    """Request body for the role update endpoint."""
    role: str  # Must be ``"user"`` or ``"admin"``


@router.patch('/users/{user_id}/role')
def update_user_role(
    user_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Promote or demote a user's role.

    Raises:
        400: Role value is not ``"user"`` or ``"admin"``.
        400: Admin attempts to change their own role (self-demotion guard).
        404: Target user does not exist.

    Returns:
        ``{id, email, role}`` of the updated user.
    """
    if payload.role not in ('user', 'admin'):
        raise HTTPException(status_code=400, detail='Role must be "user" or "admin"')
    if user_id == admin.id:
        # Prevent an admin from accidentally locking themselves out
        raise HTTPException(status_code=400, detail='You cannot change your own role')
    try:
        user = user_repo.update_role(db, user_id, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {'id': user.id, 'email': user.email, 'role': user.role}


@router.get('/users/{user_id}/history')
def get_user_history(
    user_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Retrieve the query history for a specific user.

    Raises:
        404: Target user does not exist.

    Returns:
        ``{user: {...}, logs: [...]}`` — user profile and chronological query list.
    """
    user = user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    logs = query_log_repo.get_by_user(db, user_id)
    return {
        'user': {'id': user.id, 'email': user.email, 'role': user.role},
        'logs': [
            {
                'id': log.id,
                'question': log.question,
                'course_code': log.course_code,
                'term': log.term,
                'duration_ms': log.duration_ms,
                'result_count': log.result_count,
                'status': log.status,
                'created_at': log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.delete('/users/{user_id}')
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Permanently delete a user account and all associated query logs.

    Query logs are removed automatically by the ``ON DELETE CASCADE`` foreign
    key constraint (added in migration 003_fix_cascade_delete).  SQLAlchemy's
    ``passive_deletes=True`` on the relationship ensures no extra SELECT is
    issued before the DELETE.

    Raises:
        400: Admin attempts to delete their own account.
        404: Target user does not exist.

    Returns:
        Confirmation message with the deleted user ID.
    """
    if user_id == admin.id:
        # Prevent an admin from accidentally removing themselves
        raise HTTPException(status_code=400, detail='You cannot delete your own account')
    try:
        user_repo.delete(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {'message': f'User {user_id} deleted'}


# ── All query logs ────────────────────────────────────────────────────────────

@router.get('/logs')
def list_all_logs(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """Return all query logs across every user, newest first.

    Used by the admin audit table to monitor system usage and debug issues.
    """
    logs = query_log_repo.get_all(db)
    return [
        {
            'id': log.id,
            'user_id': log.user_id,
            'question': log.question,
            'course_code': log.course_code,
            'term': log.term,
            'duration_ms': log.duration_ms,
            'result_count': log.result_count,
            'status': log.status,
            'created_at': log.created_at.isoformat(),
        }
        for log in logs
    ]


# ── Ingest trigger ────────────────────────────────────────────────────────────

@router.post('/ingest')
def trigger_ingest(_admin=Depends(require_admin)):
    """Re-run the data ingestion pipeline from the Excel source file.

    Executes ``scripts/ingest.py`` as a subprocess (blocking, up to 10 minutes).
    The last 2 000 characters of stdout/stderr are returned for diagnostics.

    Raises:
        500: Ingest script exited with a non-zero return code.

    Returns:
        ``{message, output}`` confirming completion.
    """
    import subprocess, sys, pathlib
    script = pathlib.Path(__file__).resolve().parents[3] / 'scripts' / 'ingest.py'
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=600
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr[-2000:])
    return {'message': 'Ingest complete', 'output': result.stdout[-2000:]}
