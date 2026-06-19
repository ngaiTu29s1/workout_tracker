import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.exercise import ExerciseMaster

@pytest.mark.asyncio
async def test_create_exercise(client: AsyncClient):
    payload = {
        "name_eng": "Test Push Press",
        "name_vie": "Đẩy ngực kiểm thử",
        "instructions": "Chỉ dùng để kiểm thử.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Shoulders",
        "secondary_muscle": ["Triceps"],
        "tags": ["push", "test"]
    }
    response = await client.post("/api/exercises", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert res_data["data"]["name_eng"] == "Test Push Press"
    assert "id" in res_data["data"]

@pytest.mark.asyncio
async def test_get_exercise(client: AsyncClient, db_session: AsyncSession):
    # Insert direct test record
    ex = ExerciseMaster(
        name_eng="Direct Test Exercise",
        tracking_type="TIME",
        primary_muscle="Core",
        tags=["core"]
    )
    db_session.add(ex)
    await db_session.commit()
    await db_session.refresh(ex)

    response = await client.get(f"/api/exercises/{ex.id}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert res_data["data"]["name_eng"] == "Direct Test Exercise"

    # Test Not Found
    response_404 = await client.get("/api/exercises/99999")
    assert response_404.status_code == 404
    assert response_404.json()["status"] == "error"

@pytest.mark.asyncio
async def test_list_exercises(client: AsyncClient, db_session: AsyncSession):
    # Create two exercises
    ex1 = ExerciseMaster(name_eng="Alpha Push Up", tracking_type="BODYWEIGHT_REPS", tags=["push"])
    ex2 = ExerciseMaster(name_eng="Beta Lat Pull", tracking_type="WEIGHT_REPS", tags=["pull"])
    db_session.add_all([ex1, ex2])
    await db_session.commit()

    # Search
    response = await client.get("/api/exercises?search=Alpha")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    assert any(x["name_eng"] == "Alpha Push Up" for x in data)

    # Filter tag
    response_tag = await client.get("/api/exercises?tag=pull")
    data_tag = response_tag.json()["data"]
    assert any(x["name_eng"] == "Beta Lat Pull" for x in data_tag)
    assert not any(x["name_eng"] == "Alpha Push Up" for x in data_tag)

@pytest.mark.asyncio
async def test_update_exercise(client: AsyncClient, db_session: AsyncSession):
    ex = ExerciseMaster(name_eng="Old Name", tracking_type="WEIGHT_REPS")
    db_session.add(ex)
    await db_session.commit()
    await db_session.refresh(ex)

    payload = {"name_eng": "New Name", "primary_muscle": "Chest"}
    response = await client.put(f"/api/exercises/{ex.id}", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["data"]["name_eng"] == "New Name"
    assert res_data["data"]["primary_muscle"] == "Chest"

@pytest.mark.asyncio
async def test_delete_exercise(client: AsyncClient, db_session: AsyncSession):
    ex = ExerciseMaster(name_eng="To Be Deleted", tracking_type="WEIGHT_REPS")
    db_session.add(ex)
    await db_session.commit()
    await db_session.refresh(ex)

    response = await client.delete(f"/api/exercises/{ex.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify not in DB
    response_get = await client.get(f"/api/exercises/{ex.id}")
    assert response_get.status_code == 404

@pytest.mark.asyncio
async def test_enrich_exercise(client: AsyncClient, db_session: AsyncSession):
    ex = ExerciseMaster(name_eng="Bench Press", tracking_type="WEIGHT_REPS")
    db_session.add(ex)
    await db_session.commit()
    await db_session.refresh(ex)

    response = await client.post(f"/api/exercises/{ex.id}/enrich")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    # Should fall back to mock and fill Vietnamese translation
    assert "Đẩy ngực" in res_data["data"]["name_vie"]
