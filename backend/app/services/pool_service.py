import os
import json
from typing import List, Optional
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.pool import ExercisePool
from backend.app.models.exercise import ExerciseMaster
from backend.app.services.exercise_service import title_case_name
from backend.app.services.search_config import (
    expand_vietnamese_terms,
    remove_vietnamese_tones,
)

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

        from sqlalchemy import or_
        
        # 1. Clean query
        cleaned_query = remove_vietnamese_tones(query).strip().lower()
        
        # 2. Query expansion based on Vietnamese keywords
        expanded_terms = expand_vietnamese_terms(cleaned_query)
        
        # 3. Build conditions
        conditions = []
        
        # Match original query words in any order
        words = [w.strip() for w in query.split() if w.strip()]
        if words:
            conditions.append(and_(*[ExercisePool.name.ilike(f"%{w}%") for w in words]))
            conditions.append(and_(*[ExercisePool.instructions_vi.ilike(f"%{w}%") for w in words]))
            conditions.append(and_(*[ExercisePool.target.ilike(f"%{w}%") for w in words]))
            conditions.append(and_(*[ExercisePool.equipment.ilike(f"%{w}%") for w in words]))
        
        # Match cleaned query words in any order
        cleaned_words = [w.strip() for w in cleaned_query.split() if w.strip()]
        if cleaned_words and cleaned_words != words:
            conditions.append(and_(*[ExercisePool.name.ilike(f"%{w}%") for w in cleaned_words]))
            conditions.append(and_(*[ExercisePool.target.ilike(f"%{w}%") for w in cleaned_words]))
            conditions.append(and_(*[ExercisePool.equipment.ilike(f"%{w}%") for w in cleaned_words]))
            
        # Add expanded English terms
        for term in expanded_terms:
            term_pattern = f"%{term}%"
            conditions.append(ExercisePool.name.ilike(term_pattern))
            
        stmt = select(ExercisePool).where(or_(*conditions)).limit(limit)
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
        """Copy pool exercise -> personal exercise_master, auto-applying cached translations if found."""
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
            from backend.app.services.exercise_service import ExerciseService
            ex_service = ExerciseService(self.db)
            return await ex_service.get_exercise(existing.id)

        # Check in enrichment_cache database table for cache match
        from backend.app.models.enrichment_cache import EnrichmentCache
        cache_key = pool_ex.name.strip().lower()
        cache_entry = await self.db.scalar(
            select(EnrichmentCache).where(EnrichmentCache.key == cache_key)
        )
        if cache_entry:
            cache_data = cache_entry.data
        else:
            cache_data = None
            # Fallback to json file if not in DB yet
            import os
            import json
            cache_path = os.path.join(os.getenv("POOL_DATA_PATH", "/app/static/pool"), "enrichment_cache.json")
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                        if cache_key in cache:
                            cache_data = cache[cache_key]
                            # Persist to database so it is cached in DB
                            new_entry = EnrichmentCache(key=cache_key, data=cache_data)
                            self.db.add(new_entry)
                            await self.db.commit()
                except Exception:
                    pass

        # 3. Create ExerciseMaster
        instructions_en = pool_ex.instructions_en
        instructions_vi = pool_ex.instructions_vi
        image_url = f"/pool/{pool_ex.image_path}" if pool_ex.image_path else None
        video_url = f"/pool/{pool_ex.gif_path}" if pool_ex.gif_path else None
        tracking_type = infer_tracking_type(pool_ex.equipment, pool_ex.category)
        pro_tips_vi = None
        pro_tips_en = None
        primary_muscle = pool_ex.muscle_group
        secondary_muscle = pool_ex.secondary_muscles or []

        if cache_data:
            if not name_vie:
                name_vie = cache_data.get("name_vie")
            instructions_en = cache_data.get("instructions_en") or instructions_en
            instructions_vi = cache_data.get("instructions_vi") or cache_data.get("instructions") or instructions_vi
            pro_tips_en = cache_data.get("pro_tips_en")
            pro_tips_vi = cache_data.get("pro_tips_vi") or cache_data.get("pro_tips")
            video_url = cache_data.get("video_url") or video_url
            image_url = cache_data.get("image_url") or image_url
            tracking_type = cache_data.get("tracking_type") or tracking_type
            primary_muscle = cache_data.get("primary_muscle") or primary_muscle
            secondary_muscle = cache_data.get("secondary_muscle") or secondary_muscle
            tags = cache_data.get("tags") or tags

        instructions = instructions_vi if instructions_vi else instructions_en
        pro_tips = pro_tips_vi if pro_tips_vi else pro_tips_en

        # Ensure we always keep/populate instructions (general fallback) and instructions_en
        instructions = instructions_vi or instructions or instructions_en
        instructions_en = instructions_en or instructions or "Perform the exercise with correct form."
        if not instructions_vi and instructions:
            instructions_vi = instructions

        pro_tips = pro_tips_vi or pro_tips or pro_tips_en
        pro_tips_en = pro_tips_en or pro_tips or "Focus on form and safety."
        if not pro_tips_vi and pro_tips:
            pro_tips_vi = pro_tips

        personal = ExerciseMaster(
            pool_id=pool_ex.id,
            name_eng=name_eng_title,
            name_vie=name_vie,
            instructions=instructions,
            instructions_en=instructions_en,
            instructions_vi=instructions_vi,
            image_url=image_url,
            video_url=video_url,
            pro_tips=pro_tips,
            pro_tips_en=pro_tips_en,
            pro_tips_vi=pro_tips_vi,
            primary_muscle=primary_muscle,
            secondary_muscle=secondary_muscle,
            tags=tags,
            tracking_type=tracking_type
        )

        self.db.add(personal)
        
        # Write-back instructions_vi to pool if pool is linked and has empty instructions_vi
        if pool_ex and instructions_vi:
            pool_ex.instructions_vi = pool_ex.instructions_vi or instructions_vi
            self.db.add(pool_ex)
            
        await self.db.commit()
        from backend.app.services.exercise_service import ExerciseService
        ex_service = ExerciseService(self.db)
        return await ex_service.get_exercise(personal.id)
