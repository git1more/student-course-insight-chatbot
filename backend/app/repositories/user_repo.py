from sqlalchemy.orm import Session
from app.db.models import User
from app.core.security import hash_password


class UserRepository:
    def create(self, db: Session, email: str, password: str, role: str = 'user') -> User:
        if self.get_by_email(db, email):
            raise ValueError('Email already registered')
        user = User(email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    def get_all(self, db: Session) -> list[User]:
        return db.query(User).order_by(User.id).all()

    def update_role(self, db: Session, user_id: int, role: str) -> User:
        user = self.get_by_id(db, user_id)
        if not user:
            raise ValueError('User not found')
        user.role = role
        db.commit()
        db.refresh(user)
        return user

    def delete(self, db: Session, user_id: int) -> None:
        user = self.get_by_id(db, user_id)
        if not user:
            raise ValueError('User not found')
        db.delete(user)
        db.commit()

    def seed_demo_users(self, db: Session) -> None:
        """Insert demo accounts if they don't exist yet."""
        for email, role in [('user@example.com', 'user'), ('admin@example.com', 'admin')]:
            if not self.get_by_email(db, email):
                self.create(db, email, 'password123', role)


user_repo = UserRepository()
