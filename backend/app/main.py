"""
FastAPI application entry point for the Student Course Insight Chatbot.

Start-up sequence (``lifespan``):
1. ``init_db()``           — create tables via SQLAlchemy ``create_all`` (if absent).
2. ``seed_demo_users()``   — insert demo accounts (user@example.com / admin@example.com).
3. Auto-ingest check       — if ``feedback_comments`` is empty and the Excel file
                             is present, kick off a background ingestion thread.

Routes are mounted from four routers:
    /auth/*    — signup, login
    /query     — insight query with privacy gate and RAG pipeline
    /history/* — per-user query history
    /admin/*   — user management, analytics, logs, ingest trigger (admin only)
"""
import sys
import pathlib
import subprocess
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.base import init_db, SessionLocal
from app.repositories.user_repo import user_repo
from app.repositories.feedback_repo import feedback_repo
from app.routers import auth, insights, history, admin


def _run_ingest():
    """Run the ingest script synchronously in a background daemon thread.

    Streams subprocess output directly to the container logs so progress is
    visible in ``docker compose logs``.  Errors are flagged but do not crash
    the app — the system remains usable; queries just return "not enough data".
    """
    excel = pathlib.Path(__file__).resolve().parents[1] / 'CommentsData06032026a.xlsx'
    script = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'ingest.py'
    if not excel.exists():
        print('[auto-ingest] Excel file not found — skipping auto-ingest.', flush=True)
        return
    print('[auto-ingest] Feedback table is empty — starting background ingest…', flush=True)
    result = subprocess.run(
        [sys.executable, str(script), '--file', str(excel), '--no-drop'],
        capture_output=False,   # stream output straight to container logs
    )
    if result.returncode == 0:
        print('[auto-ingest] Done.', flush=True)
    else:
        print('[auto-ingest] Ingest exited with errors.', flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """ASGI lifespan handler — runs once at startup, then yields for normal requests."""
    # 1. Ensure schema exists (idempotent — uses CREATE TABLE IF NOT EXISTS)
    init_db()

    db = SessionLocal()
    try:
        # 2. Insert demo accounts if they don't already exist
        user_repo.seed_demo_users(db)

        # 3. Trigger background data ingestion if the feedback table is empty
        if feedback_repo.count_by_filter(db, program='', year=None) == 0:
            # count_by_filter with empty program always returns 0 — check total rows instead
            from app.db.models import FeedbackComment
            total = db.query(FeedbackComment).count()
            if total == 0:
                # Daemon thread: won't block shutdown if still running
                thread = threading.Thread(target=_run_ingest, daemon=True)
                thread.start()
    finally:
        db.close()

    yield  # Application handles requests between yield and context-manager exit


# ── Application instance ──────────────────────────────────────────────────────

app = FastAPI(title=settings.app_name, lifespan=lifespan)

# CORS: allow all origins (frontend served from Vite dev server or nginx).
# ``allow_credentials=False`` is required when ``allow_origins=['*']``.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ── Router registration ───────────────────────────────────────────────────────

app.include_router(auth.router)       # /auth/signup, /auth/login
app.include_router(insights.router)   # /query, /insights/programs, /insights/years
app.include_router(history.router)    # /history
app.include_router(admin.router)      # /admin/*


# ── Utility endpoints ─────────────────────────────────────────────────────────

@app.get('/')
def root():
    """Simple liveness check — confirms the API is reachable."""
    return {'message': 'Student Course Insight Chatbot – Final Demo'}


@app.get('/health')
def health():
    """Health probe used by Docker Compose and load balancers."""
    return {'status': 'ok'}
