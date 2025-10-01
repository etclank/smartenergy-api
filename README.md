# SmartEnergy API

[![CI](https://github.com/etclank/smartenergy-api/actions/workflows/ci.yml/badge.svg)](https://github.com/etclank/smartenergy-api/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/etclank/smartenergy-api/branch/main/graph/badge.svg)](https://codecov.io/gh/etclank/smartenergy-api)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

A modern FastAPI + Postgres + Redis starter project.  
It demonstrates async APIs, JWT authentication, caching, background tasks, containerization, and CI/CD with GitHub Actions.  

This repo is the foundation for larger projects (like a production-grade “Smart Energy” backend) while staying lightweight enough for demos and portfolio use.

---

## 🚀 Tech Stack (2025)

| Layer        | Choice                                       | Notes                                   |
| ------------ | -------------------------------------------- | --------------------------------------- |
| Runtime      | **Python 3.13**                              | Poetry-managed dependencies             |
| Web API      | **FastAPI 0.115+**                           | Async REST endpoints, auto Swagger/Redoc |
| DB           | **PostgreSQL (Neon free tier)**              | Async SQLAlchemy 2.0 ORM + Alembic      |
| Cache        | **Redis (Upstash free tier)**                | Used for caching/rate-limits            |
| Auth         | JWT (python-jose)                            | One public + one protected route        |
| Containers   | Docker / docker-compose                      | Dev: API + Postgres + Redis             |
| CI/CD        | GitHub Actions                               | Ruff lint, mypy type check, pytest + coverage |

---

## 🗂️ Project Structure

```bash
.
├── README.md
├── .env.example
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py              # pydantic-settings: DB/Redis/JWT/ENV flags
│   ├── db.py                  # async SQLAlchemy engine/session
│   ├── deps.py                # FastAPI Depends (db session, auth)
│   ├── security.py            # JWT utils
│   ├── api/
│   │   ├── routers.py         # include_router hub
│   │   ├── auth.py            # /auth/login, /auth/me
│   │   ├── health.py          # /healthz
│   │   ├── meters.py          # CRUD for meters
│   │   └── schemas.py         # Pydantic models
│   ├── models/
│   │   └── meter.py           # SQLAlchemy model
│   ├── tasks/                 # (future) background tasks
│   └── telemetry.py           # (future) observability hooks
├── chart/
│   └── templates/
├── docker/
│   └── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── poetry.lock
└── tests/
    ├── test_health.py
    ├── test_auth.py
    └── test_meters.py
```
## 🧪 Quick Start
### Run locally
```bash
poetry install
poetry run uvicorn app.main:app --reload
```

Docs available at:
- Swagger → http://127.0.0.1:8000/docs
- ReDoc → http://127.0.0.1:8000/redoc

### With Docker Compose
```bash
docker compose up --build
```
This starts:
- API at http://localhost:8000
- Postgres on port 5432
- Redis on port 6379

### Run tests
```bash
poetry run pytest --maxfail=1 --disable-warnings -q
```

## ✅ Features (Definition of Done for starter)

- [x] Health endpoint (/healthz)
- [x] JWT auth (/auth/login, /auth/me)
- [x] CRUD resource: /meters
- [x] Async SQLAlchemy + Alembic migrations
- [x] Redis cache placeholder (future: rate limit)
- [x] Docker + docker-compose for dev
- [x] Pytest suite (unit & integration)
- [x] GitHub Actions CI (lint, type, test, coverage badge)
- [] “Deploy to Render” badge + hosted demo

## Next Steps
- Add Redis-backed rate limiting (FastAPI-Limiter).
- Add background task example (Celery or FastAPI BackgroundTasks).
- Set up Render free service deployment + “Deploy to Render” badge in README.
- Extend tests to cover auth edge cases and Redis caching.
- Add code coverage + status badges (Codecov/GitHub).

## 🔗 Links
- Swagger Docs → http://localhost:8000/docs
 (local)
- GitHub Actions → Actions tab
- Postgres → Neon free tier
- Redis → Upstash free tier