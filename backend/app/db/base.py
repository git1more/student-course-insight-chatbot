from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Wait for Postgres to be ready, then create pgvector extension and all tables."""
    import time
    from sqlalchemy.exc import OperationalError

    for attempt in range(1, 31):
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            break
        except OperationalError:
            print(f"[init_db] Postgres not ready (attempt {attempt}/30), retrying in 2s…")
            time.sleep(2)
    else:
        raise RuntimeError("Could not connect to Postgres after 30 attempts.")

    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
