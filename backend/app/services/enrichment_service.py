from sqlalchemy.ext.asyncio import AsyncSession

class EnrichmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def enrich_exercise(self, exercise_id: int):
        # Placeholder
        pass
