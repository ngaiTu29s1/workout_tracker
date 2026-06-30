# Fitness OS — Agent Guide

## Project structure

```
├── backend/         FastAPI + SQLAlchemy 2.0 async (Python 3.12)
│   ├── app/
│   │   ├── main.py          FastAPI app entrypoint
│   │   ├── config.py        pydantic-settings, reads .env
│   │   ├── database.py      async engine + session factory
│   │   ├── models/          SQLAlchemy ORM models
│   │   ├── routers/         FastAPI routers
│   │   ├── schemas/         Pydantic request/response schemas
│   │   ├── services/        Business logic layer
│   │   └── seed/            Seed data (1,324 exercises)
│   ├── migrations/          Alembic (async)
│   └── tests/               pytest + pytest-asyncio
├── frontend/        Served statically by FastAPI (no build step)
│   ├── index.html           Shell with Alpine.js x-data="app"
│   ├── js/
│   │   ├── app.js           Alpine data init, partial loader, routing
│   │   ├── api.js           Fetch wrapper (get/post/put/delete)
│   │   └── stores/          Alpine stores (exercise, calendar, workout, stats, pool)
│   ├── partials/            HTML fragments loaded by fetch()
│   └── css/                 6 CSS files (variables, base, components, layout, animations, views)
├── data/exercise-pool/      Static pool assets, mounted at /app/static/pool → served at /pool/
├── docker-compose.yml       Dev setup (volumes mount code, --reload)
├── docker-compose.prod.yml  Prod setup (uses pre-built image, --workers 4)
└── .env                     Required: DB creds, n8n webhook URLs, API key
```

## Running the app

```sh
docker compose up --build
```

This starts PostgreSQL 16 + FastAPI on port 8000. Alembic migrations run automatically at startup.

The app is fully open inside the Tailnet (API key auth was removed).

## Frontend (no build step)

- **No npm, no bundler.** Alpine.js (3.x), Chart.js (4.4.1), and SortableJS (1.15) are loaded from CDN at runtime.
- **No SSR.** Partials (`frontend/partials/*.html`) are fetched by `app.js` via `fetch()` and injected into `index.html` divs.
- **Routing:** hash-based (`#catalog`, `#calendar`, `#session`, `#stats`). Default view is `#session`.
- **Cache busting:** All JS imports use `?v=4` suffix. Bump when deploying changes.
- **Bilingual (vi/en):** Toggled via `Alpine.store('app').lang`. No page reload.
- **API base:** `/api` (see `frontend/js/api.js`).

## Backend

- **Entrypoint:** `backend.app.main:app` (FastAPI app with lifespan handler).
- **Config:** `backend/app/config.py` reads `.env` via pydantic-settings.
- **Testing mode:** Set `TESTING=True` to skip DB init and seeding in lifespan.
- **API responses** use envelope: `{ data: ..., message: "...", status: "ok" }`.
- **Database:** PostgreSQL 16, async via asyncpg + SQLAlchemy 2.0 async.
- **Tables:**
  - `exercise_master` — personal exercises (tracking_type: `WEIGHT_REPS`, `BODYWEIGHT_REPS`, `TIME`)
  - `exercise_pool` — pre-seeded catalog of 1,324 items (separate from master)
  - `weekly_presets` — weekly routine schedule (day_of_week 1=Sunday..7=Saturday)
  - `daily_workout_log` — workout journal with JSONB tracking_data
  - `workout_aggregated_stats` — precomputed analytics for Chart.js
  - `enrichment_cache` — AI enrichment cache
- **n8n webhooks** (external, not in repo):
  - `N8N_WEBHOOK_URL` — enrich exercise metadata
  - `N8N_AUTOFILL_WEBHOOK_URL` — autofill workout suggestions
  - Webhook failures in CI are handled with `JSON.stringify()` to prevent shell breakage.

## Testing

```sh
docker compose exec fitness-backend sh -c "env PYTHONPATH=. pytest backend/tests/ -v"
```

- **Requires running database** (tests run inside Docker container).
- Uses separate `fitness_os_test` database (created automatically by conftest).
- `conftest.py` sets `TESTING=True` and creates/drops tables per session.
- Each test gets a clean DB (rows deleted via `DELETE FROM` before each test).
- `pytest.ini`: `asyncio_mode = auto`, `asyncio_default_fixture_loop_scope = function`.

## CI/CD (GitHub Actions)

- **Trigger:** Push to `main` touching `backend/**`, `frontend/**`, `Dockerfile`, `docker-compose*`, or the workflow.
- **Pipeline:** test → build-and-push → trigger-deploy (n8n webhook).
- **Test step:** Runs `docker compose up --build`, waits for DB health check, then `docker compose exec` to run pytest, then `docker compose down -v`.

## Important conventions

- JS stores import `api.js` and register with `Alpine.store()` in an `alpine:init` listener.
- `frontend/js/app.js` also defines `customConfirm()` and Toast notification event (`window.dispatchEvent(new CustomEvent('toast', ...))`).
- Frontend filtering uses Vietnamese accent-stripping (`removeVietnameseTones()`).
- The Vietnamese search helpers (`remove_vietnamese_tones`, `VIETNAMESE_SEARCH_MAPPING`, `expand_vietnamese_terms`) live in `backend/app/services/search_config.py` (extracted from `pool_service.py`). Pure-function unit tests are in `backend/tests/test_pool_search.py`.
- `exercise_master` has 3 sets of text fields: `instructions`/`instructions_en`/`instructions_vi` and `pro_tips`/`pro_tips_en`/`pro_tips_vi`. Legacy single-field and bilingual pairs coexist.
- Pool exercises reference local assets via `pool_image`/`pool_gif` properties (`/pool/...`).
- `.handoffs/` directory is ephemeral inter-agent communication (gitignored).

## Developer tooling

- **Linter/formatter:** Ruff, configured in `pyproject.toml` (`[tool.ruff]`). Rule set: `E, F, W, I, B, SIM` (legacy `E711` `!= None` violations in untouched files are out of scope — run `ruff check --fix` to clean later).
- **Pre-commit hooks:** `.pre-commit-config.yaml` runs Ruff (check+fix+format) and standard hygiene hooks (trailing whitespace, EOF, YAML/TOML validation, large-file guard). Run once: `pre-commit install`.
- **Dev dependencies:** `backend/requirements-dev.txt` (adds `ruff` + `pre-commit` on top of `requirements.txt`). NOT installed in the runtime Docker image.
- Verify locally: `docker compose run --rm --no-deps --entrypoint sh fitness-backend -c 'pip install -q ruff && ruff check backend && ruff format --check backend'`

## What's not in this repo

- No typechecker config (mypy/pyright) yet — Ruff covers lint + format only.
- No production `Dockerfile` in the root (docker-compose builds from `backend/Dockerfile`).
