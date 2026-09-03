from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/signup', response_model=TokenResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    try:
        result = auth_service.signup(db, payload.email, payload.password, payload.role)
        return TokenResponse(access_token=result['access_token'], role=result['role'])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post('/login', response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        result = auth_service.login(db, payload.email, payload.password)
        return TokenResponse(access_token=result['access_token'], role=result['role'])
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.post('/logout')
def logout():
    # JWT is stateless; client should discard the token.
    # A full implementation would add the token to a server-side denylist.
    return {'message': 'Logged out successfully'}
