import os
import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.exercise import ExerciseMaster
from backend.app.models.pool import ExercisePool
from backend.app.seed.seed_data import seed_pool, seed_personal_defaults, auto_apply_cache
from backend.app.services.exercise_service import ExerciseService
from backend.app.schemas.exercise import ExerciseCreate, ExerciseUpdate
from backend.app.models.enrichment_cache import EnrichmentCache

CACHE_PATH = os.path.join(os.getenv("POOL_DATA_PATH", "/app/static/pool"), "enrichment_cache.json")

@pytest.fixture(scope="session", autouse=True)
def setup_test_cache():
    # Back up existing cache file if any
    backup_path = CACHE_PATH + ".bak"
    has_backup = False
    if os.path.exists(CACHE_PATH):
        try:
            os.rename(CACHE_PATH, backup_path)
            has_backup = True
        except Exception:
            pass

    # Create dummy pool directory if not exists
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

    # Write test cache data
    test_cache = {
        "cable incline fly": {
            "name_vie": "Ép ngực dốc cache",
            "instructions_vi": "Cách tập ép ngực dốc từ cache.",
            "instructions_en": "Cable incline fly en instructions from cache.",
            "pro_tips_vi": "Mẹo tập ép ngực dốc từ cache.",
            "pro_tips_en": "Pro tips en from cache.",
            "primary_muscle": "Chest",
            "tags": ["push", "chest", "isolation"],
            "tracking_type": "WEIGHT_REPS"
        },
        "one arm swing": {
            "name_vie": "Vung tạ một tay",
            "instructions_vi": "Cách tập vung tạ một tay.",
            "instructions_en": "One arm swing instruction.",
            "pro_tips_vi": "Mẹo vung tạ một tay.",
            "pro_tips_en": "Keep core tight.",
            "primary_muscle": "Full Body",
            "tags": ["legs", "core", "cardio"],
            "tracking_type": "WEIGHT_REPS"
        }
    }

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(test_cache, f, ensure_ascii=False, indent=2)

    yield

    # Clean up and restore backup
    if os.path.exists(CACHE_PATH):
        try:
            os.remove(CACHE_PATH)
        except Exception:
            pass

    if has_backup:
        try:
            os.rename(backup_path, CACHE_PATH)
        except Exception:
            pass

@pytest.mark.asyncio
async def test_cache_auto_apply_on_seed(db_session: AsyncSession):
    # 1. Seed the pool and personal defaults (which includes "cable incline fly")
    await seed_pool(db_session)
    await seed_personal_defaults(db_session)

    # Verify cable incline fly is in DB but has default translations or is none (since seed defaults handles it)
    stmt = select(ExerciseMaster).where(ExerciseMaster.name_eng == "Cable Incline Fly")
    fly = (await db_session.execute(stmt)).scalar_one_or_none()
    assert fly is not None
    
    # 2. Run auto_apply_cache
    await auto_apply_cache(db_session)

    # A. Existing "Cable Incline Fly" is updated with cached info
    stmt_updated = select(ExerciseMaster).where(ExerciseMaster.name_eng == "Cable Incline Fly")
    fly_updated = (await db_session.execute(stmt_updated)).scalar_one_or_none()
    assert fly_updated.name_vie == "Ép ngực dốc cache"
    assert fly_updated.instructions_vi == "Cách tập ép ngực dốc từ cache."
    assert fly_updated.pro_tips_vi == "Mẹo tập ép ngực dốc từ cache."

    # Verify that pool is enriched with instructions_vi
    stmt_pool = select(ExercisePool).where(ExercisePool.name == "cable incline fly")
    pool_fly = (await db_session.execute(stmt_pool)).scalar_one_or_none()
    assert pool_fly is not None
    assert pool_fly.instructions_vi == "Cách tập ép ngực dốc từ cache."

    # B. Missing "One Arm Swing" is automatically created from cache
    stmt_swing = select(ExerciseMaster).where(ExerciseMaster.name_eng == "One Arm Swing")
    swing = (await db_session.execute(stmt_swing)).scalar_one_or_none()
    assert swing is not None
    assert swing.name_vie == "Vung tạ một tay"
    assert swing.instructions_vi == "Cách tập vung tạ một tay."
    assert swing.primary_muscle == "Full Body"
    assert "cardio" in swing.tags

@pytest.mark.asyncio
async def test_cache_auto_apply_on_create(db_session: AsyncSession):
    # 1. Manually create an exercise "one arm swing" via ExerciseService
    # and verify it gets cache-applied immediately at creation
    service = ExerciseService(db_session)
    schema = ExerciseCreate(
        name_eng="one arm swing",
        tracking_type="WEIGHT_REPS"
    )
    
    new_ex = await service.create_exercise(schema)
    assert new_ex.name_eng == "One Arm Swing"
    assert new_ex.name_vie == "Vung tạ một tay"
    assert new_ex.instructions_vi == "Cách tập vung tạ một tay."
    assert new_ex.pro_tips_vi == "Mẹo vung tạ một tay."
    assert new_ex.primary_muscle == "Full Body"

@pytest.mark.asyncio
async def test_cache_auto_apply_on_add_from_pool(db_session: AsyncSession):
    from backend.app.services.pool_service import PoolService
    # 1. Seed pool
    await seed_pool(db_session)

    # 2. Get Cable Incline Fly from pool
    stmt_pool = select(ExercisePool).where(ExercisePool.name == "cable incline fly")
    pool_fly = (await db_session.execute(stmt_pool)).scalar_one()

    # 3. Add to personal (should auto-apply cached instructions_vi and write back to pool)
    service = PoolService(db_session)
    personal_ex = await service.add_to_personal(pool_id=pool_fly.id, tags=["push"])

    assert personal_ex.instructions_vi == "Cách tập ép ngực dốc từ cache."
    
    # Reload pool_fly to make sure database has written it back
    await db_session.refresh(pool_fly)
    assert pool_fly.instructions_vi == "Cách tập ép ngực dốc từ cache."

@pytest.mark.asyncio
async def test_cache_deleted_on_exercise_delete_and_rename(db_session: AsyncSession):
    # 1. Seed the pool, personal defaults, and run auto_apply_cache to populate Cache
    await seed_pool(db_session)
    await seed_personal_defaults(db_session)
    await auto_apply_cache(db_session)

    # Verify we have "Cable Incline Fly" in personal and in cache
    stmt = select(ExerciseMaster).where(ExerciseMaster.name_eng == "Cable Incline Fly")
    fly = (await db_session.execute(stmt)).scalar_one_or_none()
    assert fly is not None

    stmt_cache = select(EnrichmentCache).where(EnrichmentCache.key == "cable incline fly")
    cache_entry = (await db_session.execute(stmt_cache)).scalar_one_or_none()
    assert cache_entry is not None

    # 2. Rename the exercise
    service = ExerciseService(db_session)
    await service.update_exercise(fly.id, ExerciseUpdate(name_eng="cable incline fly renamed"))

    # Verify old cache key is deleted
    stmt_cache = select(EnrichmentCache).where(EnrichmentCache.key == "cable incline fly")
    cache_entry = (await db_session.execute(stmt_cache)).scalar_one_or_none()
    assert cache_entry is None

    # 3. Delete the exercise
    # Let's recreate "One Arm Swing" from cache first to test delete
    schema = ExerciseCreate(
        name_eng="one arm swing",
        tracking_type="WEIGHT_REPS"
    )
    new_ex = await service.create_exercise(schema)
    
    # Verify cache entry for "one arm swing" is present (as it was loaded or generated)
    stmt_cache = select(EnrichmentCache).where(EnrichmentCache.key == "one arm swing")
    cache_entry = (await db_session.execute(stmt_cache)).scalar_one_or_none()
    assert cache_entry is not None

    # Now delete the exercise
    await service.delete_exercise(new_ex.id)

    # Verify cache entry is deleted
    stmt_cache = select(EnrichmentCache).where(EnrichmentCache.key == "one arm swing")
    cache_entry = (await db_session.execute(stmt_cache)).scalar_one_or_none()
    assert cache_entry is None
