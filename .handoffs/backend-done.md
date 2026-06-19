# Handoff: Backend → Frontend

**Worker**: Backend
**Status**: ✅ DONE
**Timestamp**: 2026-06-19T17:15:50+07:00

---

## What Was Done

- [x] **Pydantic Schemas** — Created validation models for all request/response payloads (`schemas/`).
- [x] **Smart Calendar Engine** — Implemented merging weekly presets, daily routine overrides, and exercise logs into a single calendar event feed.
- [x] **Auto Stats Engine** — Automatically computes Training Volume, Max Weight, and Total Reps on workout log completion and updates them in DB via `UPSERT`.
- [x] **Exercises CRUD** — Implemented full CRUD with search query and JSONB array checks for tags and muscles.
- [x] **AI Enrichment Fallback** — Created `enrichment_service.py` to trigger n8n LLM webhooks. Added a smart Mock Data fallback if n8n is offline or unconfigured.
- [x] **Database Seeding** — Automatically seeds 23 exercises and default weekly presets (Push/Pull/Legs) on boot if database is empty.
- [x] **Uniform Error Formatting** — Handled validation and HTTP exceptions globally, formatting all errors into `{"detail": ..., "status": "error"}`.
- [x] **Docker Compose Hot-Reload** — Mounted the backend directory and enabled uvicorn `--reload` so backend code updates hot-reload instantly.
- [x] **Automated Tests** — Added 8 integration and unit tests under `tests/` covering CRUD, logging, overrides, and stats calculation. All tests passed.

---

## Current State

### Running Services
- PostgreSQL 16 → running on port `5432` inside container `db-1`.
- FastAPI backend → running on port `8000` inside container `backend-1` (exposed to host `http://localhost:8000`).
- Uvicorn hot-reload → active. Changes to files in `backend/` are applied immediately.

### Database State
- 5 tables automatically created and initialized:
  - `exercise_master` (pre-seeded with 23 exercises)
  - `weekly_presets` (pre-seeded with 7 presets)
  - `daily_workout_log` (empty)
  - `daily_overrides` (empty, holds calendar overrides)
  - `workout_aggregated_stats` (empty)

---

## API Endpoints Available

All endpoints return envelope: `{"data": ..., "message": "Success", "status": "ok"}`.

### 1. Exercise Catalog
- `GET /api/exercises` — List exercises (supports query parameters: `search`, `tag`, `muscle`).
- `GET /api/exercises/{id}` — Get single exercise by ID.
- `POST /api/exercises` — Create a new exercise.
- `PUT /api/exercises/{id}` — Update an exercise.
- `DELETE /api/exercises/{id}` — Delete an exercise.
- `POST /api/exercises/{id}/enrich` — Trigger n8n enrichment (will use mock data if webhook is offline).
  - *Example call*: `curl -X POST http://localhost:8000/api/exercises/2/enrich`

### 2. Weekly Presets
- `GET /api/presets` — Get 7-day presets routine.
- `PUT /api/presets/{day}` — Update a single day preset (day: 1 to 7).
- `PUT /api/presets` — Bulk update presets.
  - *Example payload*: `{"presets": [{"day_of_week": 1, "routine_tag": "rest"}, ...]}`

### 3. Workout Logs
- `GET /api/workouts?date=YYYY-MM-DD` — Retrieve logs for a specific date (defaults to today).
- `POST /api/workouts` — Create/Log sets for an exercise.
  - *Example payload*: `{"workout_date": "2026-06-19", "exercise_id": 1, "tracking_data": [{"set": 1, "kg": 60, "rep": 10}], "is_completed": true}`
- `PUT /api/workouts/{id}` — Update tracking data / sets of a log.
- `DELETE /api/workouts/{id}` — Delete a log (associated stats are cascade-deleted).
- `POST /api/workouts/{id}/complete?completed=true` — Toggle log completion (triggers auto stats update).

### 4. Smart Calendar
- `GET /api/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD` — Get calendar event feed.
- `POST /api/calendar/override` — Override routine for a specific date (does not change presets).
  - *Example payload*: `{"workout_date": "2026-06-17", "routine_tag": "push"}` (pass `"routine_tag": null` to revert to preset).

### 5. Statistics
- `GET /api/stats/exercise/{id}?range=30d` — Progress history of an exercise.
- `GET /api/stats/overview?range=30d` — Overall metrics dashboard (workouts, active days, volume, reps, activity map).

---

## Files Created/Modified

```
workout_checker/
├── docker-compose.yml          ← MODIFIED (added backend volumes and command hot-reload)
├── backend/
│   ├── requirements.txt        ← MODIFIED (added pytest, pytest-asyncio)
│   ├── pytest.ini              ← NEW (asyncio test configs)
│   ├── app/
│   │   ├── main.py             ← MODIFIED (added DB seeding and global exception handlers)
│   │   ├── database.py         ← MODIFIED (implemented NullPool for testing)
│   │   ├── models/
│   │   │   ├── __init__.py     ← MODIFIED (exported DailyOverride)
│   │   │   └── preset.py       ← MODIFIED (added DailyOverride model)
│   │   ├── schemas/            ← NEW (all Pydantic validation schemas)
│   │   ├── services/           ← NEW (exercise, workout, calendar, stats, enrichment)
│   │   ├── seed/               ← NEW (exercises list + presets list + seed_db function)
│   │   └── routers/            ← NEW (exercises, presets, workouts, calendar, stats endpoints)
│   └── tests/                  ← NEW (conftest.py, test_exercises.py, test_workouts.py, test_calendar.py)
```

---

## Known Issues / Notes

- **AI Enrichment**: The `N8N_WEBHOOK_URL` points to a local domain by default. In development, clicking "Fill AI" triggers a mock metadata generation which translates English names to Vietnamese, fills guidelines, and tags. This allows immediate GUI simulation.
- **Test Execution**: Tests run against the PostgreSQL database in Docker and clear tables beforehand. To execute them:
  `docker compose exec backend python -m pytest backend/tests/ -v`

---

## What Next Worker Needs To Do

Frontend worker should now build the client-side SPA in `frontend/`:
1. **SPA Router**: Setup hash-based router in `js/app.js` (`#catalog`, `#calendar`, `#session`, `#stats`, `#settings`).
2. **Alpine.js Stores & API Client**: Implement `js/api.js` to call the REST backend and write global Alpine stores to manage state.
3. **Exercise Catalog View**: Bind exercises to cards, integrate search input, tags filters, edit metadata forms, and wire the "Fill AI" button to trigger the `/enrich` endpoint.
4. **Calendar View**: Build a week/month schedule. Integrate **SortableJS** to enable drag-and-drop routine tag editing and call `POST /api/calendar/override` to persist changes.
5. **Workout Session View**: Design big finger-friendly buttons (min 48px) for log entries. Input set/kg/rep and trigger `POST /api/workouts` on save.
6. **Dashboard View**: Bind `GET /api/stats/overview` and `GET /api/stats/exercise/{id}` metrics to **Chart.js** trends graphs.
