import datetime
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.workout_log import DailyWorkoutLog
from backend.app.schemas.workout import WorkoutLogCreate, WorkoutLogUpdate
from backend.app.services.stats_service import StatsService

class WorkoutService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_workout_logs_by_date(self, workout_date: datetime.date) -> List[DailyWorkoutLog]:
        """
        Get all workout logs for a specific date, including the exercise details.
        """
        query = (
            select(DailyWorkoutLog)
            .where(DailyWorkoutLog.workout_date == workout_date)
            .options(joinedload(DailyWorkoutLog.exercise))
            .order_by(DailyWorkoutLog.id.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_workout_log_by_id(self, log_id: int) -> Optional[DailyWorkoutLog]:
        """
        Retrieve a single workout log by ID.
        """
        query = (
            select(DailyWorkoutLog)
            .where(DailyWorkoutLog.id == log_id)
            .options(joinedload(DailyWorkoutLog.exercise))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def log_workout(self, schema: WorkoutLogCreate) -> DailyWorkoutLog:
        """
        Create a new workout log or update an existing one if a log for
        the same exercise and date already exists.
        Then, automatically calculate and update aggregated statistics.
        """
        # Convert Pydantic schemas in tracking_data to lists of dicts for DB storage
        tracking_data_dict = [s.model_dump() for s in schema.tracking_data]

        # Check if daily workout log already exists for this date and exercise
        query = select(DailyWorkoutLog).where(
            and_(
                DailyWorkoutLog.workout_date == schema.workout_date,
                DailyWorkoutLog.exercise_id == schema.exercise_id
            )
        )
        result = await self.db.execute(query)
        db_log = result.scalar_one_or_none()

        if db_log:
            # Update existing
            db_log.tracking_data = tracking_data_dict
            db_log.is_completed = schema.is_completed
        else:
            # Create new
            db_log = DailyWorkoutLog(
                workout_date=schema.workout_date,
                exercise_id=schema.exercise_id,
                tracking_data=tracking_data_dict,
                is_completed=schema.is_completed
            )
            self.db.add(db_log)

        await self.db.commit()
        await self.db.refresh(db_log)

        # Trigger stats recalculation
        stats_svc = StatsService(self.db)
        await stats_svc.calculate_metrics(db_log.id)

        # Fetch with loaded exercise details for returning to client
        return await self.get_workout_log_by_id(db_log.id)

    async def update_workout_log(self, log_id: int, schema: WorkoutLogUpdate) -> Optional[DailyWorkoutLog]:
        """
        Update an existing workout log and recalculate stats.
        """
        db_log = await self.get_workout_log_by_id(log_id)
        if not db_log:
            return None

        update_data = schema.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_log, key, value)

        await self.db.commit()
        await self.db.refresh(db_log)

        # Recalculate stats
        stats_svc = StatsService(self.db)
        await stats_svc.calculate_metrics(db_log.id)

        return db_log

    async def delete_workout_log(self, log_id: int) -> bool:
        """
        Delete a workout log by ID. Stats are automatically cascade deleted at DB level.
        """
        db_log = await self.get_workout_log_by_id(log_id)
        if not db_log:
            return False

        await self.db.delete(db_log)
        await self.db.commit()
        return True

    async def complete_workout_log(self, log_id: int, is_completed: bool) -> Optional[DailyWorkoutLog]:
        """
        Mark a workout log as completed (or not) and update stats.
        """
        db_log = await self.get_workout_log_by_id(log_id)
        if not db_log:
            return None

        db_log.is_completed = is_completed
        await self.db.commit()
        await self.db.refresh(db_log)

        # Recalculate stats
        stats_svc = StatsService(self.db)
        await stats_svc.calculate_metrics(db_log.id)

        return db_log
