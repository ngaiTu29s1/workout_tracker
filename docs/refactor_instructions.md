# Refactoring Instructions - 5 Key Weaknesses

This document outlines the detailed requirements and steps to execute the refactoring of Fitness OS. Follow the instructions step-by-step, running tests and committing changes separately for each task.

---

## 1. Gộp logic fallback trùng lặp trong `enrichment_service.py`

### Requirements
- Create a private helper method `_resolve_bilingual_field(self, exercise, base_field, enriched_data, default)` in `EnrichmentService` in [enrichment_service.py](file:///app/backend/app/services/enrichment_service.py).
- The helper must return a tuple `(base_val, en_val, vi_val)` after resolving the fallbacks:
  1. Inherit from `exercise.pool` if it exists.
  2. Inherit from `enriched_data` (matching `base_field_en`, `base_field_vi`, or fallback `base_field`).
  3. Apply general fallback rules: `base_val` inherits `vi_val` -> `base_val` -> `en_val`; `en_val` inherits `en_val` -> `base_val` -> `default`; `vi_val` inherits `vi_val` -> `base_val`.
- Replace the duplicate blocks for `instructions` and `pro_tips` in `enrich_exercise` using this helper.
- Verify using tests:
  ```bash
  docker compose exec backend env PYTHONPATH=. pytest backend/tests/test_ai_suggest.py backend/tests/test_cache_auto_apply.py -v
  ```

---

## 2. Thêm Alembic migration thay vì `Base.metadata.create_all`

### Requirements
- Add `alembic>=1.13.0` to [requirements.txt](file:///app/backend/requirements.txt).
- Initialize Alembic using the async template inside `backend/`:
  - Run `alembic init -t async backend/migrations` from `/app`.
- Update `alembic.ini`:
  - Set `script_location = backend/migrations`.
- Update `backend/migrations/env.py`:
  - Import `Base` from `backend.app.database`.
  - Import all models from `backend.app.models` (so they register on `Base.metadata`).
  - Set `target_metadata = Base.metadata`.
  - Retrieve the database connection URL from `backend.app.config.settings.DATABASE_URL`.
- Generate the initial migration:
  ```bash
  docker compose exec backend alembic revision --autogenerate -m "initial_schema"
  ```
- Modify [database.py](file:///app/backend/app/database.py):
  - Remove `await conn.run_sync(Base.metadata.create_all)` from `init_db()`.
- Update uvicorn start scripts to run migrations before uvicorn:
  - In [docker-compose.yml](file:///app/docker-compose.yml) and [docker-compose.prod.yml](file:///app/docker-compose.prod.yml), update u`command` to:
    ```bash
    sh -c "alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"
    ```
  - In [Dockerfile](file:///app/backend/Dockerfile), update the CMD to run migrations using shell form.
- Test seeding and verify database setup.

---

## 3. Thêm Authentication tối thiểu (API Key) cho `/api/*`

### Requirements
- Add `API_SECRET_KEY` config setting in [config.py](file:///app/backend/app/config.py):
  - Type: `str`, Default: `"change_me_api_key_fitness_os_123"`.
- Implement `verify_api_key` dependency inside a new file `backend/app/auth.py` checking the header `X-API-Key`. Raise 401 Unauthorized if invalid.
- Apply this dependency to all routers in [main.py](file:///app/backend/app/main.py):
  ```python
  app.include_router(exercises, dependencies=[Depends(verify_api_key)])
  # Repeat for presets, workouts, calendar, stats, pool
  ```
- Exclude the static files mounts `/`, `/pool` and `/docs` / `/openapi.json` from protection.
- Update [api.js](file:///app/frontend/js/api.js):
  - Automatically read the key from `localStorage.getItem('FITNESS_OS_API_KEY')`. If empty, prompt the user once and save it.
  - Inject the header `X-API-Key` into all fetch requests.
  - In `handleResponse`, if status is 401, clear the stored key and reload the page to force a re-prompt.
- Update [.env.example](file:///app/.env.example) and compose files to include `API_SECRET_KEY`.
- Update [conftest.py](file:///app/backend/tests/conftest.py) to inject `X-API-Key` automatically in the `client` fixture:
  ```python
  client.headers.update({"X-API-Key": settings.API_SECRET_KEY})
  ```

---

## 4. Tách `index.html` monolithic thành các phần nhỏ hơn

### Requirements
- Create directory `frontend/partials/`.
- Split large UI sections from [index.html](file:///app/frontend/index.html) into individual files:
  - `frontend/partials/catalog.html`
  - `frontend/partials/calendar.html`
  - `frontend/partials/session.html`
  - `frontend/partials/stats.html`
  - `frontend/partials/modals.html`
- Inside [index.html](file:///app/frontend/index.html), replace the extracted sections with empty divs:
  ```html
  <div id="partial-catalog"></div>
  <div id="partial-calendar"></div>
  <div id="partial-session"></div>
  <div id="partial-stats"></div>
  <div id="partial-modals"></div>
  ```
- Add a `loadPartials()` helper in [app.js](file:///app/frontend/js/app.js) to fetch and inject partials into their containers.
- Delay loading of Alpine.js scripts at the end of [app.js](file:///app/frontend/js/app.js) until `loadPartials()` completes:
  ```javascript
  loadPartials()
    .then(() => loadScript('...collapse...'))
    .then(() => loadScript('...alpine...'))
  ```
- Manually test that all views, modals, and store bindings function correctly.

---

## 5. Sửa rủi ro `x-html` và an toàn hoá cache enrichment

### Requirements
- In [index.html](file:///app/frontend/index.html) (or `session.html` partial after splitting), replace the `x-html` directive that interpolates `routineTag` with secure static text blocks using `x-text` inside nested elements:
  ```html
  <p class="text-secondary mb-md">
      <span x-text="lang === 'vi' ? 'Hôm nay bạn tập ' : 'Today you train '"></span>
      <strong x-text="($store.workout.routineTag || '').toUpperCase().replace('_', ' ')"></strong>
      <span x-text="lang === 'vi' ? '. Chưa có bài tập nào được lên lịch.' : '. No exercises scheduled yet.'"></span>
  </p>
  ```
- To safely support concurrent writes under multiple workers/containers, migrate the JSON file cache to a Postgres table:
  - Create model `EnrichmentCache` in `backend/app/models/enrichment_cache.py` with `key` (String, primary key), `data` (JSONB), and `updated_at`.
  - Update `seed_data.py` to auto-populate the table if it's empty by importing the existing `enrichment_cache.json` if available.
  - Update `pool_service.py` and `enrichment_service.py` to query and save to the `enrichment_cache` table instead of reading/writing to `enrichment_cache.json`.
- Run tests and ensure all are green.
