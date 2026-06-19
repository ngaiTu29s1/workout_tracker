from sqlalchemy.ext.asyncio import AsyncSession

class ExerciseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_exercises(self):
        # Placeholder
        return []
