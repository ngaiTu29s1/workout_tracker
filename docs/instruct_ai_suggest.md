# Specs: Split Workout Programming (Local vs AI Suggestions)

This document specifies how to split the workout programming autofill feature into two distinct, user-controlled paths: **Local Suggestions (Tự lên lịch)** and **AI Suggestions (AI gợi ý)**.

---

## 1. Core Requirements

### A. Two Separate UI Paths
When the user's daily session is empty, instead of a single auto-suggest button, the UI must present two clear, separate actions:
1. **Local Fill (Tự lên lịch)**: Uses backend database logic to fetch exercises and apply progressive overload rules locally without any external LLM call.
2. **AI Suggest (AI gợi ý)**: Sends data to the n8n webhook for LLM processing. If the webhook is not configured, it must show an error/warning to the user.

### B. Webhook Placeholder & Configuration Check
* If the `N8N_AUTOFILL_WEBHOOK_URL` is empty, missing, or contains a placeholder value (like `"change_me"`, `"placeholder"`, or `"local"`), the **AI Suggest** endpoint must explicitly fail with a `400 Bad Request` status and a message indicating the webhook is not configured.
* The frontend must intercept this error and display a Toast alert: *"N8N Webhook chưa được cấu hình. Vui lòng thiết lập N8N_AUTOFILL_WEBHOOK_URL trong file .env."* (or equivalent English text).
* The **Local Fill** path must function fully without requiring any webhook configuration.

---

## 2. Backend Design Changes

### A. Split Endpoint Routers in `backend/app/routers/workouts.py`
Add or adapt endpoints to separate the paths:

* `POST /api/workouts/local-suggest`:
  - Body: `{ "date": "YYYY-MM-DD", "routine_tag": "push" }`
  - Logic: Call `WorkoutService.get_local_suggestions(date, routine_tag)`
  
* `POST /api/workouts/ai-suggest`:
  - Body: `{ "date": "YYYY-MM-DD", "routine_tag": "push" }`
  - Logic: Verify `N8N_AUTOFILL_WEBHOOK_URL` is configured. If not, raise `HTTPException(status_code=400, detail="N8N Webhook not configured")`. Otherwise, call `WorkoutService.get_ai_suggestions(date, routine_tag)`.

* `POST /api/workouts/local-swap` & `POST /api/workouts/ai-swap`:
  - Split the swap endpoint similarly. `local-swap` will strictly use the local candidate database matching logic. `ai-swap` will check the webhook configuration and send the request to n8n, raising a 400 if unconfigured.

* `POST /api/workouts/apply-suggestions`:
  - Single endpoint to write the suggestions array to the DB (works for both paths).

### B. Update Service Logic in `backend/app/services/workout_service.py`
* Clean up `get_ai_suggestions` and `swap_ai_suggestion` so they strictly perform webhook calls and raise errors/warnings if the webhook URL is unconfigured. Do not automatically fall back to local logic.
* Implement `get_local_suggestions` and `swap_local_suggestion` containing the smart rule-based database selection and progressive overload calculations.

---

## 3. Frontend Design Changes

### A. Double Button Layout in `frontend/index.html`
* Update the empty state banner card:
  - If routine is not `rest`, render two primary-style actions:
    1. `<button @click="$store.workout.fetchLocalSuggestions()">⚙️ Tự lên lịch</button>`
    2. `<button @click="$store.workout.fetchAiSuggestions()">🪄 AI gợi ý</button>`
* Update the Session Header:
  - Provide a dropdown or split buttons if appropriate, or keep both icons visible for quick access.

### B. Update Store Actions in `frontend/js/stores/workout-store.js`
* Maintain distinct states or a source tracker:
  - `aiSuggestions`: Holds the suggestions for preview.
  - `suggestionSource`: `'local'` or `'ai'` (to track which swap endpoint to call when swapping).
* Implement actions:
  - `fetchLocalSuggestions()`: Calls `/api/workouts/local-suggest`, sets `suggestionSource = 'local'`.
  - `fetchAiSuggestions()`: Calls `/api/workouts/ai-suggest`, sets `suggestionSource = 'ai'`.
  - `swapSuggestion(exerciseId)`: Checks `suggestionSource`. If `'local'`, calls `/api/workouts/local-swap`; if `'ai'`, calls `/api/workouts/ai-swap`.

### C. Preview Modal Header
* Update the Preview Modal Title to match the source:
  - If `suggestionSource === 'local'`: *"Xem trước buổi tập (Lên lịch tự động)"*
  - If `suggestionSource === 'ai'`: *"Xem trước buổi tập (AI gợi ý)"*

---

## 4. Verification Plan

### A. Automated Tests
* Update `backend/tests/test_ai_suggest.py` (or add `backend/tests/test_workout_programming.py`) to verify:
  1. `/api/workouts/local-suggest` returns 5-6 exercises with overload targets when logs exist.
  2. `/api/workouts/ai-suggest` returns `400 Bad Request` when `N8N_AUTOFILL_WEBHOOK_URL` is unset or set to a placeholder.
  3. `/api/workouts/local-swap` successfully replaces an exercise with a same-muscle alternative.

### B. Manual Verification
1. Unset `N8N_AUTOFILL_WEBHOOK_URL` in `.env` (or set it to `change_me`).
2. Click **🪄 AI gợi ý** on the UI empty state and verify a toast warning displays: *"N8N Webhook chưa được cấu hình..."*
3. Click **⚙️ Tự lên lịch** and verify the preview modal opens with 5-6 exercises.
4. Test check/uncheck, swap (`🔄`), and apply. Verify logs are written to the database.
