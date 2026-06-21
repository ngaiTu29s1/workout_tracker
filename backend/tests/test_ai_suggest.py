import pytest
import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.exercise import ExerciseMaster
from backend.app.models.workout_log import DailyWorkoutLog
from backend.app.config import settings

@pytest.mark.asyncio
async def test_local_suggest_endpoint(client: AsyncClient, db_session: AsyncSession):
    # Setup exercises with tags
    ex1 = ExerciseMaster(
        name_eng="Bench Press",
        tags=["push"],
        primary_muscle="Chest",
        tracking_type="WEIGHT_REPS"
    )
    ex2 = ExerciseMaster(
        name_eng="Overhead Press",
        tags=["push"],
        primary_muscle="Shoulders",
        tracking_type="WEIGHT_REPS"
    )
    db_session.add_all([ex1, ex2])
    await db_session.commit()
    await db_session.refresh(ex1)
    await db_session.refresh(ex2)

    # Fetch local suggestions (should work without n8n configuration)
    payload = {
        "date": "2026-06-21",
        "routine_tag": "push"
    }
    response = await client.post("/api/workouts/local-suggest", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    suggestions = res_data["data"]
    assert len(suggestions) >= 2
    
    # Assert suggestions contain our exercise IDs
    suggested_ids = [s["exercise_id"] for s in suggestions]
    assert ex1.id in suggested_ids
    assert ex2.id in suggested_ids


@pytest.mark.asyncio
async def test_local_swap_endpoint(client: AsyncClient, db_session: AsyncSession):
    # Setup candidate exercises with same tag and muscle
    ex1 = ExerciseMaster(
        name_eng="Flat Bench Press",
        tags=["push"],
        primary_muscle="Chest",
        tracking_type="WEIGHT_REPS"
    )
    ex2 = ExerciseMaster(
        name_eng="Incline Fly",
        tags=["push"],
        primary_muscle="Chest",
        tracking_type="WEIGHT_REPS"
    )
    ex3 = ExerciseMaster(
        name_eng="Cable Crossover",
        tags=["push"],
        primary_muscle="Chest",
        tracking_type="WEIGHT_REPS"
    )
    db_session.add_all([ex1, ex2, ex3])
    await db_session.commit()
    await db_session.refresh(ex1)
    await db_session.refresh(ex2)
    await db_session.refresh(ex3)

    # Swap ex1 (Flat Bench Press), currently suggesting ex1 and ex2 (Incline Fly).
    # Expected candidate should be ex3 (Cable Crossover) because ex2 is in current_suggestions.
    payload = {
        "date": "2026-06-21",
        "routine_tag": "push",
        "exercise_id": ex1.id,
        "current_suggestions": [ex1.id, ex2.id]
    }
    response = await client.post("/api/workouts/local-swap", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    replacement = res_data["data"]
    assert replacement["exercise_id"] == ex3.id


@pytest.mark.asyncio
async def test_ai_suggest_unconfigured(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    # Set the webhook URL to a placeholder
    monkeypatch.setattr(settings, "N8N_AUTOFILL_WEBHOOK_URL", "change_me")
    
    payload = {
        "date": "2026-06-21",
        "routine_tag": "push"
    }
    response = await client.post("/api/workouts/ai-suggest", json=payload)
    assert response.status_code == 400
    res_data = response.json()
    assert "not configured" in res_data["detail"].lower()


@pytest.mark.asyncio
async def test_ai_swap_unconfigured(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings, "N8N_AUTOFILL_WEBHOOK_URL", "change_me")
    
    payload = {
        "date": "2026-06-21",
        "routine_tag": "push",
        "exercise_id": 1,
        "current_suggestions": [1, 2]
    }
    response = await client.post("/api/workouts/ai-swap", json=payload)
    assert response.status_code == 400
    res_data = response.json()
    assert "not configured" in res_data["detail"].lower()


@pytest.mark.asyncio
async def test_apply_suggestions_endpoint(client: AsyncClient, db_session: AsyncSession):
    # Setup exercise
    ex = ExerciseMaster(
        name_eng="Triceps Pushdown",
        tags=["push"],
        primary_muscle="Triceps",
        tracking_type="WEIGHT_REPS"
    )
    db_session.add(ex)
    await db_session.commit()
    await db_session.refresh(ex)

    # Apply suggestions
    payload = {
        "date": "2026-06-21",
        "suggestions": [
            {
                "exercise_id": ex.id,
                "suggested_sets": [
                    {"set": 1, "kg": 20.0, "rep": 12},
                    {"set": 2, "kg": 22.5, "rep": 10}
                ]
            }
        ]
    }
    response = await client.post("/api/workouts/apply-suggestions", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    logs = res_data["data"]
    assert len(logs) == 1
    assert logs[0]["exercise_id"] == ex.id
    assert len(logs[0]["tracking_data"]) == 2
    assert logs[0]["is_completed"] is False

    # Verify directly in DB
    from datetime import date
    query = select(DailyWorkoutLog).where(DailyWorkoutLog.workout_date == date(2026, 6, 21))
    result = await db_session.execute(query)
    db_logs = result.scalars().all()
    assert len(db_logs) == 1
    assert db_logs[0].exercise_id == ex.id
    assert db_logs[0].is_completed is False
    assert db_logs[0].tracking_data[0]["kg"] == 20.0


@pytest.mark.asyncio
async def test_ai_apply_endpoint(client: AsyncClient, db_session: AsyncSession):
    # Setup exercise for compatibility check
    ex = ExerciseMaster(
        name_eng="Cable Pushdown",
        tags=["push"],
        primary_muscle="Triceps",
        tracking_type="WEIGHT_REPS"
    )
    db_session.add(ex)
    await db_session.commit()
    await db_session.refresh(ex)

    payload = {
        "date": "2026-06-21",
        "suggestions": [
            {
                "exercise_id": ex.id,
                "suggested_sets": [
                    {"set": 1, "kg": 15.0, "rep": 15}
                ]
            }
        ]
    }
    response = await client.post("/api/workouts/ai-apply", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"


@pytest.mark.asyncio
async def test_suggest_sets_endpoint(client: AsyncClient, db_session: AsyncSession):
    # Setup exercise
    ex = ExerciseMaster(
        name_eng="Hammer Strength Bench",
        tags=["push"],
        primary_muscle="Chest",
        tracking_type="WEIGHT_REPS"
    )
    db_session.add(ex)
    await db_session.commit()
    await db_session.refresh(ex)

    # 1. Try non-existent ID (should return 404)
    resp = await client.get("/api/workouts/suggest-sets?exercise_id=9999")
    assert resp.status_code == 404

    # 2. Try existing exercise with no history (should return 3 empty sets)
    resp = await client.get(f"/api/workouts/suggest-sets?exercise_id={ex.id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["exercise_id"] == ex.id
    assert len(data["suggested_sets"]) == 3
    assert data["suggested_sets"][0]["kg"] is None

    # 3. Log a completed workout for this exercise
    log = DailyWorkoutLog(
        exercise_id=ex.id,
        workout_date=datetime.date(2026, 6, 20),
        is_completed=True,
        tracking_data=[
            {"set": 1, "kg": 20.0, "rep": 10},
            {"set": 2, "kg": 20.0, "rep": 10}
        ]
    )
    db_session.add(log)
    await db_session.commit()

    # 4. Try again, should now suggest progressive overload (+2.5kg)
    resp = await client.get(f"/api/workouts/suggest-sets?exercise_id={ex.id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["suggested_sets"]) == 2
    assert data["suggested_sets"][0]["kg"] == 22.5
    assert data["suggested_sets"][0]["rep"] == 10

