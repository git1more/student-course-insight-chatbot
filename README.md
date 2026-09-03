# Student Course Insight Chatbot

**Team:** 9900-W16B-ALMOND | **Course:** COMP9900 26T1 | **Final Demo**

## Project Overview

A web application that helps academic staff explore anonymised student feedback through a natural-language query interface. The system combines semantic retrieval (RAG) and structured LLM-based summarisation to generate evidence-grounded, six-part insight reports from student comments.

### Key Features
- Natural-language query over anonymised course feedback
- Semantic retrieval via OpenAI embeddings + pgvector cosine similarity
- Structured six-part academic report (GPT-4o-mini)
- Privacy gate — blocks results when fewer than 10 comments match
- JWT authentication with role-based access (user / admin)
- Query history with one-click re-run
- Admin dashboard: user management, analytics, logs, data ingestion

---

## Repository Structure

```
.
├── backend/                        # FastAPI backend
│   ├── app/
│   │   ├── core/                   # Config, JWT, dependencies
│   │   ├── db/                     # SQLAlchemy models & session
│   │   ├── repositories/           # Data access layer
│   │   ├── routers/                # API endpoints (auth, insights, history, admin)
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   └── services/               # Business logic (RAG, LLM, privacy, auth)
│   ├── scripts/ingest.py           # Excel → PostgreSQL data pipeline
│   ├── tests/                      # Pytest unit & integration tests
│   └── requirements.txt
├── frontend/                       # React 18 + Vite frontend
│   ├── src/
│   │   ├── api/                    # Fetch client with JWT injection
│   │   ├── components/             # Layout, InsightResult, ProtectedRoute
│   │   ├── context/                # AuthContext, ToastContext
│   │   ├── pages/                  # QueryPage, HistoryPage, AdminPage, LoginPage
│   │   └── __tests__/              # Vitest unit tests
│   └── package.json
├── docker-compose.yml              # Three-service deployment (db, backend, frontend)
├── .env.example                    # Environment variable template
├── CommentsData06032026a.xlsx      # Source feedback dataset
└── README.md
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, React Router v6, Vite |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL 16 + pgvector |
| AI/ML | OpenAI `text-embedding-3-small` (1536-dim), `gpt-4o-mini` |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Containerisation | Docker Compose |
| Testing | pytest, pytest-cov (backend); Vitest, React Testing Library (frontend) |

---

## Quick Start (Docker — Recommended)

### Prerequisites
- Docker Desktop (with Docker Compose)
- An OpenAI API key

### Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd finaldemo

# 2. Create environment file
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY

# 3. Build and start all services
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

Demo accounts are seeded automatically:

| Email | Password | Role |
|-------|----------|------|
| user@example.com | password123 | user |
| admin@example.com | password123 | admin |

Data is ingested automatically from `CommentsData06032026a.xlsx` on first startup (requires valid OpenAI API key).

### Reset database

```bash
docker compose down -v   # removes volume, recreates schema on next start
docker compose up --build
```

---

## Local Development Setup (without full Docker)

### Database only (via Docker)
```bash
docker compose up db -d
```

### Backend
```bash
cd backend
pip install -r requirements.txt
python scripts/ingest.py --file ../CommentsData06032026a.xlsx
python run.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```env
DATABASE_URL=postgresql://insight:insight_pass@localhost:5432/insight_db
SECRET_KEY=replace-with-a-long-random-secret
OPENAI_API_KEY=sk-...your-key-here...
```

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Secret for JWT signing (use a long random string) |
| `OPENAI_API_KEY` | Required for embeddings and LLM responses |

> **Security note:** Never commit `.env` to version control. The `.gitignore` already excludes it.

---

## Testing

### Backend Tests (pytest)

```bash
cd backend
pip install pytest pytest-cov
pytest tests/ -v --cov=app --cov-report=term-missing
```

No database or OpenAI API key required — all external dependencies are mocked.

#### Test files

| File | Type | What is tested |
|------|------|---------------|
| `test_security.py` | Unit | Password hashing, JWT encode/decode, tampered token |
| `test_privacy_service.py` | Unit | Confidence bands, sample-size gate boundary values |
| `test_user_repo.py` | Unit | User CRUD — create, find, update role, delete |
| `test_auth_service.py` | Unit | signup/login happy + sad paths |
| `test_auth_router.py` | Unit | HTTP status codes, input validation, error messages |
| `test_insights_router.py` | Unit | Privacy gate (n=0/9/10), six-part response structure |
| `test_admin_router.py` | Unit | Role toggle, self-demotion guard, delete, 403 for non-admin |
| `test_integration.py` | Integration | Full auth flow, query→history, admin flow, token edge cases |

#### Happy and sad cases covered
- Correct credentials → 200 with token
- Wrong password → 401
- Duplicate email → 400
- Missing required field → 422
- Expired / tampered JWT → 401/403
- Privacy gate at n=9 (blocked) and n=10 (passes)
- Admin self-delete → 400
- Admin self-demotion → 400
- Non-admin accessing admin routes → 403

#### Mocking strategy
All SQLAlchemy sessions are replaced with `MagicMock`. External services (OpenAI) are patched at the service layer using `unittest.mock.patch`. Tests run fully offline.

### Frontend Tests (Vitest + React Testing Library)

```bash
cd frontend
npm install
npm test
```

#### Test files

| File | What is tested |
|------|---------------|
| `client.test.js` | Authorization header injection, error throwing on 4xx/5xx, missing token |
| `AuthContext.test.jsx` | login/logout state changes, sessionStorage persistence, session restore |
| `ToastContext.test.jsx` | Toast renders, auto-dismiss at 4s, multiple toasts, independent timers |

#### Mocking strategy
`fetch` is replaced with `vi.fn()`. `sessionStorage` is cleared between tests. Fake timers (`vi.useFakeTimers`) control toast dismissal without real delays.

---

## System Architecture

```
Browser (React)
    │  HTTP + Bearer JWT
    ▼
FastAPI Backend
    ├── /auth/*      → AuthService → UserRepository → PostgreSQL
    ├── /query       → PrivacyGate → RAGService → EmbeddingService → pgvector
    │                             → LLMService → OpenAI GPT-4o-mini
    │                             → QueryLogRepository → PostgreSQL
    ├── /history     → QueryLogRepository → PostgreSQL
    └── /admin/*     → UserRepository / QueryLogRepository / AnalyticsService
```

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| Query generation fails | Check `OPENAI_API_KEY` is set and valid in `.env` |
| Ingestion skipped at startup | Ensure `CommentsData06032026a.xlsx` is in project root |
| Frontend cannot reach backend | Confirm backend is running on port 8000 |
| Delete user fails | Run `docker compose down -v && docker compose up --build` to reset DB schema |
| Port already in use | Change port mapping in `docker-compose.yml` (e.g. `5174:80`) |

---

## Known Limitations

- Requires a valid OpenAI API key for embeddings and LLM responses
- Dataset is limited to the supplied feedback file
- Feedback contains only improvement-oriented comments; the system flags this in every report
- Not hardened for production (no rate limiting, no HTTPS, demo credentials)

---

## Project Context

Developed as a capstone project for COMP9900 26T1 at UNSW Sydney.
**Team 9900-W16B-ALMOND:** Juncheng Zhang, Yangfan Tong, Yifan Song, Zhen Yang, Linhong Gong, Siyuan Zhao
