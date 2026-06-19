# Handoff: Backend → Frontend

**Worker**: Backend
**Status**: ✅ DONE
**Timestamp**: 2026-06-19T23:10:00+07:00

---

## What Was Done

- [x] **Database Seeding Overhaul** — Cleaned, corrected, and expanded the default exercises seed to **33 classic exercises** in [seed_data.py](file:///home/tu/Documents/Projects/workout_checker/backend/app/seed/seed_data.py).
  - Cleaned all `video_url` and `image_url` placeholder assets to `None` so they can be enriched dynamically later.
  - Reviewed and refined all exercise `instructions` and `pro_tips` in Vietnamese for fitness science accuracy.
  - Ensured correct anatomical terms for target muscles (e.g. replacing placeholder strings like `"Cardio"` with `"Quads"`, `"Back"`, etc.).
  - Verified and adjusted routine tags (`push`, `pull`, `legs`) and descriptor tags (`upper_body`, `lower_body`, `compound`, `isolation`, `barbell`, `dumbbell`, `cable`, `machine`, `bodyweight`) for every exercise.
- [x] **Volume Reset and Verification** — Nuked the Docker PostgreSQL volume (`docker compose down -v`) and rebuilt the environment to re-seed clean data. Verified exactly **33 exercises** are retrieved from `GET /api/exercises`.
- [x] **Pydantic Schemas** — Created validation models for all request/response payloads (`schemas/`).
- [x] **Smart Calendar Engine** — Implemented merging weekly presets, daily routine overrides, and exercise logs into a single calendar event feed.
- [x] **Auto Stats Engine** — Automatically computes Training Volume, Max Weight, and Total Reps on workout log completion and updates them in DB via `UPSERT`.
- [x] **Exercises CRUD** — Implemented full CRUD with search query and JSONB array checks for tags and muscles.
- [x] **AI Enrichment Fallback** — Created `enrichment_service.py` to trigger n8n LLM webhooks. Added a smart Mock Data fallback if n8n is offline or unconfigured.
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
  - `exercise_master` (pre-seeded with **33 clean exercises**)
  - `weekly_presets` (pre-seeded with 7 presets)
  - `daily_workout_log` (empty)
  - `daily_overrides` (empty, holds calendar overrides)
  - `workout_aggregated_stats` (empty)

## API Endpoints & Payload Specifications

> [!TIP]
> **Interactive API Documentation (Swagger/OpenAPI)**:
> - Interactive Swagger UI is available at: `http://localhost:8000/docs`
> - Static documentation via ReDoc is available at: `http://localhost:8000/redoc`
> - Raw OpenAPI JSON schema (for AI Agents / Client generation): `http://localhost:8000/openapi.json`

All responses wrap their payload inside a standard response envelope:
```json
{
  "data": { ... },
  "message": "Success",
  "status": "ok"
}
```
In case of errors, the format is uniformly:
```json
{
  "detail": "Error message details",
  "status": "error"
}
```

---

### 1. Exercise Catalog

#### `GET /api/exercises`
* **Description**: Returns all exercises (supports filtering by query params `search`, `tag`, `muscle`).
* **Response Envelope Payload (`data`)**:
```json
[
  {
    "id": 19,
    "name_eng": "Barbell Back Squat",
    "name_vie": "Gánh tạ đòn sau (Squat)",
    "instructions": "Đặt tạ đòn trên cơ cầu vai. Hạ hông xuống...",
    "video_url": null,
    "image_url": null,
    "pro_tips": "Luôn giữ bàn chân bám chặt trên sàn...",
    "tracking_type": "WEIGHT_REPS",
    "primary_muscle": "Quads",
    "secondary_muscle": ["Glutes", "Hamstrings", "Core"],
    "tags": ["legs", "lower_body", "compound", "barbell"],
    "created_at": "2026-06-19T23:09:31.947"
  }
]
```

#### `POST /api/exercises`
* **Description**: Adds a new exercise.
* **Request Payload**:
```json
{
  "name_eng": "Dumbbell Flyes",
  "name_vie": "Ép ngực tạ đơn ghế phẳng",
  "instructions": "Nằm ngửa trên ghế phẳng, cầm tạ dang rộng hai bên...",
  "pro_tips": "Khủy tay hơi cong cố định suốt hành trình.",
  "tracking_type": "WEIGHT_REPS",
  "primary_muscle": "Chest",
  "secondary_muscle": ["Shoulders"],
  "tags": ["push", "upper_body", "isolation", "dumbbell"]
}
```

#### `POST /api/exercises/{id}/enrich`
* **Description**: Triggers n8n / AI enrichment to fill translations, guidelines, muscles, and tags.
* **Response Envelope Payload (`data`)**: Returns the updated `ExerciseMaster` object showing populated parameters.

---

### 2. Weekly Presets

#### `GET /api/presets`
* **Description**: Retrieves the 7-day default routine preset.
* **Response Envelope Payload (`data`)**:
```json
[
  {"day_of_week": 1, "routine_tag": "rest"},
  {"day_of_week": 2, "routine_tag": "push"},
  {"day_of_week": 3, "routine_tag": "pull"},
  {"day_of_week": 4, "routine_tag": "legs"},
  {"day_of_week": 5, "routine_tag": "push"},
  {"day_of_week": 6, "routine_tag": "pull"},
  {"day_of_week": 7, "routine_tag": "legs"}
]
```

#### `PUT /api/presets`
* **Description**: Bulk updates weekly presets.
* **Request Payload**:
```json
{
  "presets": [
    {"day_of_week": 1, "routine_tag": "rest"},
    {"day_of_week": 2, "routine_tag": "push"},
    {"day_of_week": 3, "routine_tag": "pull"},
    {"day_of_week": 4, "routine_tag": "rest"},
    {"day_of_week": 5, "routine_tag": "push"},
    {"day_of_week": 6, "routine_tag": "pull"},
    {"day_of_week": 7, "routine_tag": "legs"}
  ]
}
```

---

### 3. Workout Logs

#### `GET /api/workouts?date=YYYY-MM-DD`
* **Description**: Gets all workout logs logged for a specific date (e.g., `2026-06-19`).
* **Response Envelope Payload (`data`)**:
```json
[
  {
    "id": 1,
    "workout_date": "2026-06-19",
    "exercise_id": 19,
    "is_completed": true,
    "tracking_data": [
      {"set": 1, "kg": 100, "rep": 8, "time_seconds": null},
      {"set": 2, "kg": 100, "rep": 8, "time_seconds": null}
    ],
    "exercise": {
      "id": 19,
      "name_eng": "Barbell Back Squat",
      "name_vie": "Gánh tạ đòn sau (Squat)",
      "tracking_type": "WEIGHT_REPS",
      "primary_muscle": "Quads",
      "tags": ["legs", "lower_body", "compound", "barbell"]
    }
  }
]
```

#### `POST /api/workouts`
* **Description**: Logs/Saves sets for an exercise on a date.
* **Request Payload**:
```json
{
  "workout_date": "2026-06-19",
  "exercise_id": 19,
  "tracking_data": [
    {"set": 1, "kg": 100, "rep": 8},
    {"set": 2, "kg": 100, "rep": 8}
  ],
  "is_completed": true
}
```

#### `PUT /api/workouts/{id}`
* **Description**: Modifies tracking data or completion status of an existing log.
* **Request Payload**:
```json
{
  "tracking_data": [
    {"set": 1, "kg": 105, "rep": 8},
    {"set": 2, "kg": 105, "rep": 7}
  ],
  "is_completed": true
}
```

---

### 4. Smart Calendar

#### `GET /api/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD`
* **Description**: Returns day-by-day routines combining presets, custom overrides, and logged logs.
* **Response Envelope Payload (`data`)**:
```json
[
  {
    "date": "2026-06-19",
    "day_of_week": 6,
    "weekday_name": "Friday",
    "routine_tag": "legs",
    "preset_tag": "pull",
    "is_override": true,
    "workout_logs": [
      {
        "id": 1,
        "exercise_id": 19,
        "is_completed": true,
        "tracking_data": [
          {"set": 1, "kg": 100, "rep": 8, "time_seconds": null}
        ],
        "exercise": {
          "id": 19,
          "name_eng": "Barbell Back Squat",
          "name_vie": "Gánh tạ đòn sau (Squat)",
          "tracking_type": "WEIGHT_REPS",
          "primary_muscle": "Quads",
          "tags": ["legs", "lower_body", "compound", "barbell"]
        }
      }
    ]
  }
]
```

#### `POST /api/calendar/override`
* **Description**: Overrides a routine on a specific day (set `routine_tag` to `null` to revert to default preset).
* **Request Payload**:
```json
{
  "workout_date": "2026-06-19",
  "routine_tag": "legs"
}
```

#### `POST /api/calendar/autofill`
* **Description**: Automatically pulls matching exercises from the database for the given date's routine tag using the n8n autofill webhook (or falls back to matching local exercises if n8n is offline).
* **Request Payload**:
```json
{
  "workout_date": "2026-06-19"
}
```
* **Response Envelope Payload (`data`)**:
```json
[
  {
    "id": 1,
    "workout_date": "2026-06-19",
    "exercise_id": 19,
    "is_completed": false,
    "tracking_data": [],
    "exercise": {
      "id": 19,
      "name_eng": "Barbell Back Squat",
      "name_vie": "Gánh tạ đòn sau (Squat)",
      "tracking_type": "WEIGHT_REPS",
      "primary_muscle": "Quads",
      "tags": ["legs", "lower_body", "compound", "barbell"]
    }
  }
]
```

---

### 5. Statistics

#### `GET /api/stats/overview?range=30d`
* **Description**: Dashboard metrics overview.
* **Response Envelope Payload (`data`)**:
```json
{
  "total_workouts": 15,
  "total_active_days": 12,
  "total_volume_kg": 18450.0,
  "total_reps": 320,
  "recent_activity": [
    {"date": "2026-06-19", "completed_count": 2},
    {"date": "2026-06-18", "completed_count": 1}
  ]
}
```

#### `GET /api/stats/exercise/{id}?range=30d`
* **Description**: Progression data of a single exercise to plot charts.
* **Response Envelope Payload (`data`)**:
```json
{
  "exercise_id": 19,
  "history": [
    {
      "date": "2026-06-19",
      "volume": 1600.0,
      "max_weight": 100.0,
      "total_reps": 16,
      "total_time": null
    }
  ]
}
```


---

## Files Created/Modified

```
workout_checker/
├── docker-compose.yml          ← MODIFIED (added backend volumes and command hot-reload)
├── .env                        ← MODIFIED (added N8N_AUTOFILL_WEBHOOK_URL)
├── .env.example                ← MODIFIED (added N8N_AUTOFILL_WEBHOOK_URL)
├── backend/
│   ├── requirements.txt        ← MODIFIED (added pytest, pytest-asyncio)
│   ├── pytest.ini              ← NEW (asyncio test configs)
│   ├── app/
│   │   ├── main.py             ← MODIFIED (added DB seeding and global exception handlers)
│   │   ├── database.py         ← MODIFIED (implemented NullPool for testing)
│   │   ├── config.py           ← MODIFIED (added dynamic db assembly + autofill config)
│   │   ├── models/
│   │   │   ├── __init__.py     ← MODIFIED (exported DailyOverride)
│   │   │   └── preset.py       ← MODIFIED (added DailyOverride model)
│   │   ├── schemas/            ← NEW (all Pydantic validation schemas)
│   │   ├── services/           ← NEW (exercise, workout, calendar, stats, enrichment)
│   │   │   └── calendar_service.py ← MODIFIED (added autofill_workout method calling n8n)
│   │   ├── seed/
│   │   │   └── seed_data.py    ← MODIFIED (revised and expanded to 33 clean, correct exercises)
│   │   └── routers/            ← NEW (exercises, presets, workouts, calendar, stats endpoints)
│   │       └── calendar.py     ← MODIFIED (added POST /api/calendar/autofill route)
│   └── tests/                  ← NEW (conftest.py, test_exercises.py, test_workouts.py, test_calendar.py)
```

---

## Known Issues / Notes

- **AI Enrichment & n8n Integration**:
  - The `N8N_WEBHOOK_URL` in `.env` is configured to integrate directly with n8n in Production mode: `https://n8n.tutran-dev.id.vn/webhook/enrich-exercise`.
  - **Payload sent to n8n**: `{"exercise_id": <int>, "name_eng": "<string>"}`.
  - **Expected response JSON from n8n**:
    ```json
    {
      "name_vie": "Tên tiếng Việt",
      "instructions": "Hướng dẫn chi tiết kỹ thuật",
      "pro_tips": "Mẹo tập luyện",
      "primary_muscle": "Nhóm cơ chính",
      "secondary_muscle": ["Nhóm cơ phụ"],
      "tags": ["legs", "lower_body", "compound"],
      "tracking_type": "WEIGHT_REPS",
      "video_url": null,
      "image_url": null
    }
    ```
- **AI Calendar Autofill**:
  - A new endpoint `POST /api/calendar/autofill` calls `N8N_AUTOFILL_WEBHOOK_URL` (`https://n8n.tutran-dev.id.vn/webhook/autofill-exercise`) to fetch suggestions for a routine tag day.
  - **Payload sent to n8n**: `{"workout_date": "YYYY-MM-DD", "routine_tag": "push"}`.
  - **Expected response JSON from n8n**:
    ```json
    {
      "exercise_ids": [1, 2, 3]
    }
    ```
  - If n8n is unconfigured or unreachable, the system queries the local database to find exercises containing the day's routine tag (e.g. `push`) and logs them automatically, ensuring full offline capability.
- **Test Execution**: Tests run against the PostgreSQL database in Docker and clear tables beforehand. To execute them:
  `docker compose exec backend env PYTHONPATH=. pytest -c backend/pytest.ini -v`

---

## What Next Worker Needs To Do

Frontend worker should now build the client-side SPA in `frontend/`:
1. **SPA Router**: Setup hash-based router in `js/app.js` (`#catalog`, `#calendar`, `#session`, `#stats`, `#settings`).
2. **Alpine.js Stores & API Client**: Implement `js/api.js` to call the REST backend and write global Alpine stores to manage state.
3. **Exercise Catalog View**: Bind exercises to cards, integrate search input, tags filters, edit metadata forms, and wire the "Fill AI" button to trigger the `/enrich` endpoint.
4. **Calendar View**: Build a week/month schedule. Integrate **SortableJS** to enable drag-and-drop routine tag editing and call `POST /api/calendar/override` to persist changes.
5. **Workout Session View**: Design big finger-friendly buttons (min 48px) for log entries. Input set/kg/rep and trigger `POST /api/workouts` on save.
6. **Dashboard View**: Bind `GET /api/stats/overview` and `GET /api/stats/exercise/{id}` metrics to **Chart.js** trends graphs.
