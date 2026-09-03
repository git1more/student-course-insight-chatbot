"""
Authentication business logic — signup and login.

This service sits between the ``/auth`` router and the data layer.  It
delegates credential storage to :mod:`~app.repositories.user_repo` and token
creation to :mod:`~app.core.security`, keeping the router thin.

Both methods return a dict containing the signed JWT and the user's role so
the frontend can immediately update its auth context without a second request.
"""
from sqlalchemy.orm import Session
from app.core.security import create_access_token, verify_password
from app.repositories.user_repo import user_repo


class AuthService:
    """Handles user registration and password-based authentication."""

    def signup(self, db: Session, email: str, password: str, role: str = 'user'):
        """Register a new user and return a JWT access token.

        Delegates to :func:`~app.repositories.user_repo.UserRepository.create`,
        which hashes the password and raises ``ValueError`` on duplicate email.

        Args:
            db:       Active database session.
            email:    New user's email address (must be unique).
            password: Plain-text password (hashed before storage).
            role:     Initial role — ``"user"`` by default; admin seeding passes ``"admin"``.

        Returns:
            ``{"access_token": str, "role": str}``

        Raises:
            ValueError: If the email is already registered (propagated from repo).
        """
        user = user_repo.create(db, email=email, password=password, role=role)
        token = create_access_token(subject=str(user.id), role=user.role)
        return {'access_token': token, 'role': user.role}

    def login(self, db: Session, email: str, password: str):
        """Authenticate an existing user and return a JWT access token.

        Looks up the user by email, then verifies the plain-text password
        against the stored PBKDF2 hash.  A deliberate vague error message
        (``"Invalid email or password"``) is used to avoid leaking which field
        was wrong.

        Args:
            db:       Active database session.
            email:    The user's registered email address.
            password: Plain-text password to verify.

        Returns:
            ``{"access_token": str, "role": str}``

        Raises:
            ValueError: If the email is not found or the password is incorrect.
        """
        user = user_repo.get_by_email(db, email)
        if not user or not verify_password(password, user.password_hash):
            # Use the same error for "not found" and "wrong password" to prevent
            # user enumeration attacks.
            raise ValueError('Invalid email or password')
        token = create_access_token(subject=str(user.id), role=user.role)
        return {'access_token': token, 'role': user.role}


# Module-level singleton — import this instance rather than the class.
auth_service = AuthService()
