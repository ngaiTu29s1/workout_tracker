# Fitness OS — Workout Tracker & Planner

Fitness OS is a mobile-first workout tracking and planning web application. This repository contains the local development infrastructure and code skeletons.

## Technology Stack

- **Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + asyncpg
- **Database**: PostgreSQL 16
- **Frontend**: HTML5 + Vanilla CSS + Alpine.js
- **Infra**: Docker Compose

---

## Project Directory Layout

```
workout_checker/
├── docker-compose.yml
├── .env.example
├── .env
├── .gitignore
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # FastAPI app entry + static serve
│       ├── config.py            # Pydantic Settings config loader
│       ├── database.py          # Async connection engine & table generator
│       ├── models/              # SQLAlchemy Models (exercise, preset, log, stats)
│       ├── schemas/             # Request/Response validation schemas
│       ├── routers/             # API Router definitions
│       └── services/            # Business logic classes
│
└── frontend/
    └── index.html               # SPA frontend container (served at /)
```

---

## Local Development Setup

### Prerequisite

- Docker and Docker Compose installed.

### Setup and Booting

1. Ensure the environment file is created. A default `.env` is initialized during setup, but you can copy/modify it if necessary:
   ```bash
   cp .env.example .env
   ```

2. Start the services using Docker Compose:
   ```bash
   docker compose up --build -d
   ```

3. View running logs:
   ```bash
   docker compose logs -f backend
   ```

4. Stop all services:
   ```bash
   docker compose down
   ```

---

## Verification & Health Check

Verify your setup by running the following commands:

- **Check service statuses**:
  ```bash
  docker compose ps
  ```

- **Query API endpoint**:
  ```bash
  curl http://localhost:8000/api/exercises
  # Expected Response: {"data":[],"message":"Success","status":"ok"}
  ```

- **Query static Frontend serving**:
  ```bash
  curl -I http://localhost:8000/
  # Expected Response: HTTP/1.1 200 OK (with Content-Type: text/html)
  ```

- **Check if database tables are generated**:
  ```bash
  docker compose exec db psql -U fitness -d fitness_os -c "\dt"
  # Expected to list: daily_workout_log, exercise_master, weekly_presets, workout_aggregated_stats
  ```
