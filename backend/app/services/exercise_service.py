import os
import json
from typing import List, Optional
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.exercise import ExerciseMaster
from backend.app.schemas.exercise import ExerciseCreate, ExerciseUpdate

def title_case_name(name: str) -> str:
    if not name:
        return name
    words = name.split()
    result = []
    for word in words:
        clean_word = word.strip("()")
        if clean_word.isupper() and len(clean_word) > 1:
            result.append(word)
        else:
            prefix = "(" if word.startswith("(") else ""
            suffix = ")" if word.endswith(")") else ""
            result.append(f"{prefix}{clean_word.capitalize()}{suffix}")
    return " ".join(result)

class ExerciseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_exercises(
        self,
        search: Optional[str] = None,
        tag: Optional[str] = None,
        muscle: Optional[str] = None
    ) -> List[ExerciseMaster]:
        """
        List all exercises, optionally filtering by search term (English/Vietnamese name),
        tag, or muscle group.
        """
        query = select(ExerciseMaster).options(joinedload(ExerciseMaster.pool))
        filters = []

        if search:
            # Case insensitive search on name_eng and name_vie
            search_pattern = f"%{search}%"
            filters.append(
                or_(
                    ExerciseMaster.name_eng.ilike(search_pattern),
                    ExerciseMaster.name_vie.ilike(search_pattern)
                )
            )

        if tag:
            # Check if tag exists in tags JSONB list
            filters.append(ExerciseMaster.tags.contains([tag]))

        if muscle:
            # Check if primary_muscle matches OR if it's in secondary_muscle JSONB list
            filters.append(
                or_(
                    ExerciseMaster.primary_muscle.ilike(muscle),
                    ExerciseMaster.secondary_muscle.contains([muscle])
                )
            )

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(ExerciseMaster.name_eng.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_exercise(self, exercise_id: int) -> Optional[ExerciseMaster]:
        """
        Retrieve a single exercise by ID.
        """
        query = select(ExerciseMaster).where(ExerciseMaster.id == exercise_id).options(joinedload(ExerciseMaster.pool))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_exercise(self, schema: ExerciseCreate) -> ExerciseMaster:
        """
        Create a new exercise in exercise_master, auto-applying cached translation/enrichment
        metadata if it exists in enrichment_cache.json.
        """
        cache_path = os.path.join(os.getenv("POOL_DATA_PATH", "/app/static/pool"), "enrichment_cache.json")
        cache_data = None
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    cache_key = schema.name_eng.strip().lower()
                    if cache_key in cache:
                        cache_data = cache[cache_key]
            except Exception:
                pass  # Fail silently and use schema fields

        name_eng = title_case_name(schema.name_eng)
        name_vie = schema.name_vie
        instructions = schema.instructions
        instructions_en = schema.instructions_en
        instructions_vi = schema.instructions_vi
        video_url = schema.video_url
        image_url = schema.image_url
        pro_tips = schema.pro_tips
        pro_tips_en = schema.pro_tips_en
        pro_tips_vi = schema.pro_tips_vi
        tracking_type = schema.tracking_type
        primary_muscle = schema.primary_muscle
        secondary_muscle = schema.secondary_muscle
        tags = schema.tags

        if cache_data:
            if not name_vie:
                name_vie = cache_data.get("name_vie")
            if not instructions_en:
                instructions_en = cache_data.get("instructions_en")
            if not instructions_vi:
                instructions_vi = cache_data.get("instructions_vi") or cache_data.get("instructions")
            if not pro_tips_en:
                pro_tips_en = cache_data.get("pro_tips_en")
            if not pro_tips_vi:
                pro_tips_vi = cache_data.get("pro_tips_vi") or cache_data.get("pro_tips")
            if not video_url:
                video_url = cache_data.get("video_url")
            if not image_url:
                image_url = cache_data.get("image_url")
            if not tracking_type:
                tracking_type = cache_data.get("tracking_type")
            if not primary_muscle:
                primary_muscle = cache_data.get("primary_muscle")
            if not secondary_muscle:
                secondary_muscle = cache_data.get("secondary_muscle")
            if not tags:
                tags = cache_data.get("tags")

        # Sync/Fallback instructions and pro_tips
        instructions = instructions_vi or instructions or instructions_en
        instructions_en = instructions_en or instructions or "Perform the exercise with correct form."
        if not instructions_vi and instructions:
            instructions_vi = instructions

        pro_tips = pro_tips_vi or pro_tips or pro_tips_en
        pro_tips_en = pro_tips_en or pro_tips or "Focus on form and safety."
        if not pro_tips_vi and pro_tips:
            pro_tips_vi = pro_tips

        db_exercise = ExerciseMaster(
            name_eng=name_eng,
            name_vie=name_vie,
            instructions=instructions,
            instructions_en=instructions_en,
            instructions_vi=instructions_vi,
            video_url=video_url,
            image_url=image_url,
            pro_tips=pro_tips,
            pro_tips_en=pro_tips_en,
            pro_tips_vi=pro_tips_vi,
            tracking_type=tracking_type,
            primary_muscle=primary_muscle,
            secondary_muscle=secondary_muscle,
            tags=tags
        )
        self.db.add(db_exercise)
        await self.db.commit()
        await self.db.refresh(db_exercise)
        return await self.get_exercise(db_exercise.id)

    async def update_exercise(self, exercise_id: int, schema: ExerciseUpdate) -> Optional[ExerciseMaster]:
        """
        Update an existing exercise.
        """
        exercise = await self.get_exercise(exercise_id)
        if not exercise:
            return None

        old_name = exercise.name_eng

        # Apply updates
        update_data = schema.model_dump(exclude_unset=True)
        if "name_eng" in update_data and update_data["name_eng"]:
            new_name = title_case_name(update_data["name_eng"])
            if new_name != old_name:
                # Also delete from enrichment_cache so that the old name is not recreated on startup/restart
                from backend.app.models.enrichment_cache import EnrichmentCache
                from sqlalchemy import delete
                old_key = old_name.strip().lower()
                await self.db.execute(delete(EnrichmentCache).where(EnrichmentCache.key == old_key))
            update_data["name_eng"] = new_name

        for key, value in update_data.items():
            setattr(exercise, key, value)

        # Write-back instructions_vi to linked pool if available
        if exercise.pool and exercise.instructions_vi:
            exercise.pool.instructions_vi = exercise.pool.instructions_vi or exercise.instructions_vi

        await self.db.commit()
        return await self.get_exercise(exercise.id)

    async def delete_exercise(self, exercise_id: int) -> bool:
        """
        Delete an exercise by ID.
        """
        exercise = await self.get_exercise(exercise_id)
        if not exercise:
            return False

        # Also delete from enrichment_cache so that it is not recreated on startup/restart
        from backend.app.models.enrichment_cache import EnrichmentCache
        from sqlalchemy import delete
        cache_key = exercise.name_eng.strip().lower()
        await self.db.execute(delete(EnrichmentCache).where(EnrichmentCache.key == cache_key))

        await self.db.delete(exercise)
        await self.db.commit()
        return True
