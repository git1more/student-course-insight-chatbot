"""
FastAPI dependency injectors for authentication and authorisation.

Usage:
    Depend on ``get_current_user`` to require a valid JWT.
    Depend on ``require_admin`` to additionally enforce the ``admin`` role.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.base import get_db
from app.repositories.user_repo import user_repo

# Parses the ``Authorization: Bearer <token>`` header from incoming requests.
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Resolve the authenticated user from a Bearer JWT.

    FastAPI injects the ``Authorization`` header via ``bearer_scheme`` and a
    database session via ``get_db``.  The token is decoded and verified; if
    valid, the corresponding ``User`` row is fetched from the database.

    Raises:
        HTTPException 401: Token is missing, expired, or tampered with.
        HTTPException 401: Token subject does not match any user in the DB.

    Returns:
        The ``User`` ORM instance for the authenticated caller.
    """
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')

    user_id = int(payload['sub'])  # 'sub' claim stores the user's database ID
    user = user_repo.get_by_id(db, user_id)
    if not user:
        # Token was valid but the account no longer exists (e.g. deleted by admin)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    return user


def require_admin(current_user=Depends(get_current_user)):
    """Extend ``get_current_user`` to enforce the ``admin`` role.

    Raises:
        HTTPException 403: The authenticated user is not an admin.

    Returns:
        The admin ``User`` ORM instance.
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin access required')
    return current_user
