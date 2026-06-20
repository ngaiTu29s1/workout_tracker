from typing import List, Optional
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.pool import ExercisePool
from backend.app.models.exercise import ExerciseMaster
from backend.app.services.exercise_service import title_case_name

def infer_tracking_type(equipment: Optional[str], category: Optional[str]) -> str:
    eq = (equipment or "").lower()
    cat = (category or "").lower()
    if "body weight" in eq:
        return "BODYWEIGHT_REPS"
    elif "cardio" in eq or "cardio" in cat or "stationary bike" in eq or "stationary bike" in cat:
        return "TIME"
    else:
        return "WEIGHT_REPS"

class PoolService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, query: str, limit: int = 20) -> List[ExercisePool]:
        """Fuzzy search pool by name. Use ILIKE for simplicity."""
        if not query:
            stmt = select(ExercisePool).limit(limit)
            res = await self.db.execute(stmt)
            return list(res.scalars().all())

        # Tách query thành words, join bằng %
        # VD: "bench press" -> "%bench%press%"
        words = query.strip().split()
        pattern = "%" + "%".join(words) + "%"
        stmt = select(ExercisePool).where(ExercisePool.name.ilike(pattern)).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_by_id(self, pool_id: int) -> Optional[ExercisePool]:
        """Get single pool exercise by DB id."""
        stmt = select(ExercisePool).where(ExercisePool.id == pool_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_categories(self) -> dict:
        """Return distinct body_parts and equipment types."""
        body_parts_stmt = select(ExercisePool.body_part).distinct().where(ExercisePool.body_part != None).order_by(ExercisePool.body_part.asc())
        equipment_stmt = select(ExercisePool.equipment).distinct().where(ExercisePool.equipment != None).order_by(ExercisePool.equipment.asc())

        bp_res = await self.db.execute(body_parts_stmt)
        eq_res = await self.db.execute(equipment_stmt)

        return {
            "body_parts": [bp for bp in bp_res.scalars().all() if bp],
            "equipment": [eq for eq in eq_res.scalars().all() if eq]
        }

    async def add_to_personal(self, pool_id: int, tags: List[str], name_vie: Optional[str] = None) -> ExerciseMaster:
        """Copy pool exercise -> personal exercise_master."""
        # 1. Fetch pool exercise
        pool_ex = await self.get_by_id(pool_id)
        if not pool_ex:
            raise ValueError(f"Exercise Pool item with ID {pool_id} not found")

        # 2. Check unique constraint for name_eng in exercise_master
        name_eng_title = title_case_name(pool_ex.name)
        stmt = select(ExerciseMaster).where(ExerciseMaster.name_eng == name_eng_title)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            # Already exists in personal, link it to pool if not linked and return
            if not existing.pool_id:
                existing.pool_id = pool_ex.id
                await self.db.commit()
                await self.db.refresh(existing)
            return existing

        # 3. Create ExerciseMaster
        instructions = pool_ex.instructions_vi if pool_ex.instructions_vi else pool_ex.instructions_en
        image_url = f"/pool/{pool_ex.image_path}" if pool_ex.image_path else None
        video_url = f"/pool/{pool_ex.gif_path}" if pool_ex.gif_path else None
        tracking_type = infer_tracking_type(pool_ex.equipment, pool_ex.category)

        personal = ExerciseMaster(
            pool_id=pool_ex.id,
            name_eng=name_eng_title,
            name_vie=name_vie,
            instructions=instructions,
            instructions_en=pool_ex.instructions_en,
            instructions_vi=pool_ex.instructions_vi,
            image_url=image_url,
            video_url=video_url,
            primary_muscle=pool_ex.muscle_group,
            secondary_muscle=pool_ex.secondary_muscles or [],
            tags=tags,
            tracking_type=tracking_type
        )

        self.db.add(personal)
        await self.db.commit()

        # Eager load pool to return
        stmt_refresh = select(ExerciseMaster).where(ExerciseMaster.id == personal.id).options(joinedload(ExerciseMaster.pool))
        res = await self.db.execute(stmt_refresh)
        return res.scalar_one()
