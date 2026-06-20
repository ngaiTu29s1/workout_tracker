import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.pool import ExercisePool
from backend.app.models.exercise import ExerciseMaster

@pytest.mark.asyncio
async def test_pool_search(client: AsyncClient, db_session: AsyncSession):
    # Seed a couple of test exercises in the pool
    p1 = ExercisePool(
        pool_id="0001",
        name="Barbell Bench Press",
        category="chest",
        body_part="chest",
        equipment="barbell",
        target="pectorals",
        instructions_en="Lie on bench, press bar.",
        instructions_vi="Nằm trên ghế, đẩy tạ.",
        muscle_group="Chest",
        secondary_muscles=["Triceps", "Shoulders"],
        image_path="images/0001.jpg",
        gif_path="videos/0001.gif"
    )
    p2 = ExercisePool(
        pool_id="0002",
        name="Dumbbell Bicep Curl",
        category="arms",
        body_part="arms",
        equipment="dumbbell",
        target="biceps",
        instructions_en="Curl dumbbell.",
        muscle_group="Biceps",
        secondary_muscles=["Forearms"],
        image_path="images/0002.jpg",
        gif_path="videos/0002.gif"
    )
    db_session.add_all([p1, p2])
    await db_session.commit()

    # Search query "bench"
    response = await client.get("/api/pool/search?q=bench")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert len(res_data["data"]) == 1
    assert res_data["data"][0]["name"] == "Barbell Bench Press"

    # Search query "bicep"
    response = await client.get("/api/pool/search?q=bicep")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

@pytest.mark.asyncio
async def test_pool_detail(client: AsyncClient, db_session: AsyncSession):
    p1 = ExercisePool(
        pool_id="0001",
        name="Barbell Bench Press",
        category="chest",
        body_part="chest",
        equipment="barbell",
        target="pectorals",
        instructions_en="Lie on bench, press bar.",
        muscle_group="Chest",
        secondary_muscles=["Triceps"],
        image_path="images/0001.jpg",
        gif_path="videos/0001.gif"
    )
    db_session.add(p1)
    await db_session.commit()
    await db_session.refresh(p1)

    response = await client.get(f"/api/pool/{p1.id}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert res_data["data"]["name"] == "Barbell Bench Press"
    assert res_data["data"]["instructions_en"] == "Lie on bench, press bar."

    # Test Not Found
    response_404 = await client.get("/api/pool/99999")
    assert response_404.status_code == 404

@pytest.mark.asyncio
async def test_pool_categories(client: AsyncClient, db_session: AsyncSession):
    p1 = ExercisePool(
        pool_id="0001",
        name="Barbell Bench Press",
        body_part="chest",
        equipment="barbell"
    )
    p2 = ExercisePool(
        pool_id="0002",
        name="Bodyweight Squat",
        body_part="legs",
        equipment="body weight"
    )
    db_session.add_all([p1, p2])
    await db_session.commit()

    response = await client.get("/api/pool/categories")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert "chest" in res_data["data"]["body_parts"]
    assert "legs" in res_data["data"]["body_parts"]
    assert "barbell" in res_data["data"]["equipment"]
    assert "body weight" in res_data["data"]["equipment"]

@pytest.mark.asyncio
async def test_add_from_pool(client: AsyncClient, db_session: AsyncSession):
    # 1. Cardio machine -> TIME
    p1 = ExercisePool(
        pool_id="0001",
        name="Treadmill Running",
        category="cardio",
        equipment="cardio machine",
        instructions_en="Run on treadmill.",
        muscle_group="Cardio",
        secondary_muscles=[],
        image_path="images/0001.jpg",
        gif_path="videos/0001.gif"
    )
    # 2. Body weight -> BODYWEIGHT_REPS
    p2 = ExercisePool(
        pool_id="0002",
        name="Standard Push Up",
        category="chest",
        equipment="body weight",
        instructions_en="Do push ups.",
        muscle_group="Chest",
        secondary_muscles=["Triceps"],
        image_path="images/0002.jpg",
        gif_path="videos/0002.gif"
    )
    db_session.add_all([p1, p2])
    await db_session.commit()
    await db_session.refresh(p1)
    await db_session.refresh(p2)

    # Add p1 to personal with tags
    payload = {
        "pool_id": p1.id,
        "tags": ["cardio", "warmup"],
        "name_vie": "Chạy bộ máy"
    }
    response = await client.post("/api/exercises/add-from-pool", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert res_data["data"]["name_eng"] == "Treadmill Running"
    assert res_data["data"]["name_vie"] == "Chạy bộ máy"
    assert res_data["data"]["tracking_type"] == "TIME"
    assert res_data["data"]["pool_id"] == p1.id
    assert res_data["data"]["pool_image"] == "/pool/images/0001.jpg"
    assert res_data["data"]["pool_gif"] == "/pool/videos/0001.gif"

    # Add p2 to personal
    payload2 = {
        "pool_id": p2.id,
        "tags": ["push"]
    }
    response2 = await client.post("/api/exercises/add-from-pool", json=payload2)
    assert response2.status_code == 200
    res_data2 = response2.json()
    assert res_data2["data"]["tracking_type"] == "BODYWEIGHT_REPS"
    assert res_data2["data"]["pool_id"] == p2.id
    assert res_data2["data"]["pool_image"] == "/pool/images/0002.jpg"

@pytest.mark.asyncio
async def test_personal_still_works(client: AsyncClient, db_session: AsyncSession):
    # Test that normal exercise CRUD still works
    payload = {
        "name_eng": "Manual Bench Press",
        "instructions": "Manual instructions.",
        "tracking_type": "WEIGHT_REPS",
        "primary_muscle": "Chest",
        "tags": ["chest"]
    }
    response = await client.post("/api/exercises", json=payload)
    assert response.status_code == 200
    assert response.json()["data"]["name_eng"] == "Manual Bench Press"
    assert response.json()["data"]["pool_id"] is None
    assert response.json()["data"]["pool_image"] is None
