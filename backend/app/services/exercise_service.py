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
        Create a new exercise in exercise_master.
        """
        db_exercise = ExerciseMaster(
            name_eng=title_case_name(schema.name_eng),
            name_vie=schema.name_vie,
            instructions=schema.instructions,
            instructions_en=schema.instructions_en,
            instructions_vi=schema.instructions_vi,
            video_url=schema.video_url,
            image_url=schema.image_url,
            pro_tips=schema.pro_tips,
            pro_tips_en=schema.pro_tips_en,
            pro_tips_vi=schema.pro_tips_vi,
            tracking_type=schema.tracking_type,
            primary_muscle=schema.primary_muscle,
            secondary_muscle=schema.secondary_muscle,
            tags=schema.tags
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

        # Apply updates
        update_data = schema.model_dump(exclude_unset=True)
        if "name_eng" in update_data and update_data["name_eng"]:
            update_data["name_eng"] = title_case_name(update_data["name_eng"])

        for key, value in update_data.items():
            setattr(exercise, key, value)

        await self.db.commit()
        await self.db.refresh(exercise)
        return exercise

    async def delete_exercise(self, exercise_id: int) -> bool:
        """
        Delete an exercise by ID.
        """
        exercise = await self.get_exercise(exercise_id)
        if not exercise:
            return False

        await self.db.delete(exercise)
        await self.db.commit()
        return True
