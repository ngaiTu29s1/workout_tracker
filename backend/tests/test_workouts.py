import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.exercise import ExerciseMaster
from backend.app.models.workout_log import DailyWorkoutLog

@pytest.mark.asyncio
async def test_log_and_update_workout(client: AsyncClient, db_session: AsyncSession):
    # Setup exercise
    ex = ExerciseMaster(name_eng="Test Deadlift", tracking_type="WEIGHT_REPS")
    db_session.add(ex)
    await db_session.commit()
    await db_session.refresh(ex)

    # 1. Log workout
    payload = {
        "workout_date": "2026-06-19",
        "exercise_id": ex.id,
        "tracking_data": [
            {"set": 1, "kg": 100.0, "rep": 5},
            {"set": 2, "kg": 110.0, "rep": 3}
        ],
        "is_completed": True
    }
    response = await client.post("/api/workouts", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert res_data["data"]["exercise_id"] == ex.id
    assert len(res_data["data"]["tracking_data"]) == 2
    log_id = res_data["data"]["id"]

    # 2. Check stats auto-calculated
    stats_response = await client.get(f"/api/stats/exercise/{ex.id}?range=30d")
    assert stats_response.status_code == 200
    stats_data = stats_response.json()["data"]
    assert stats_data["exercise_id"] == ex.id
    assert len(stats_data["history"]) == 1
    # Volume = 100*5 + 110*3 = 500 + 330 = 830
    assert stats_data["history"][0]["volume"] == 830.0
    assert stats_data["history"][0]["max_weight"] == 110.0
    assert stats_data["history"][0]["total_reps"] == 8

    # 3. Update workout log
    update_payload = {
        "tracking_data": [
            {"set": 1, "kg": 100.0, "rep": 5},
            {"set": 2, "kg": 110.0, "rep": 3},
            {"set": 3, "kg": 120.0, "rep": 1}
        ]
    }
    update_response = await client.put(f"/api/workouts/{log_id}", json=update_payload)
    assert update_response.status_code == 200
    assert len(update_response.json()["data"]["tracking_data"]) == 3

    # 4. Verify stats updated automatically
    stats_response = await client.get(f"/api/stats/exercise/{ex.id}?range=30d")
    stats_data = stats_response.json()["data"]
    # New Volume = 830 + 120*1 = 950
    assert stats_data["history"][0]["volume"] == 950.0
    assert stats_data["history"][0]["max_weight"] == 120.0
    assert stats_data["history"][0]["total_reps"] == 9

    # 5. Toggle completion
    comp_response = await client.post(f"/api/workouts/{log_id}/complete?completed=false")
    assert comp_response.status_code == 200
    assert comp_response.json()["data"]["is_completed"] is False

    # Stats should be removed because log is not completed
    stats_response = await client.get(f"/api/stats/exercise/{ex.id}?range=30d")
    assert len(stats_response.json()["data"]["history"]) == 0

    # 6. Delete log
    del_response = await client.delete(f"/api/workouts/{log_id}")
    assert del_response.status_code == 200
    assert del_response.json()["status"] == "ok"
