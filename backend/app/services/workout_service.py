from sqlalchemy.ext.asyncio import AsyncSession

class WorkoutService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_workout_log(self, date):
        # Placeholder
        return []
