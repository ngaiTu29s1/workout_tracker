import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.models.preset import WeeklyPreset, DailyOverride
from backend.app.models.workout_log import DailyWorkoutLog

class CalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_db_weekday(self, dt: datetime.date) -> int:
        """
        Convert python date to database weekday notation:
        1 = Sunday, 2 = Monday, 3 = Tuesday, 4 = Wednesday, 5 = Thursday, 6 = Friday, 7 = Saturday
        """
        return ((dt.weekday() + 1) % 7) + 1

    async def get_calendar_events(self, start_date: datetime.date, end_date: datetime.date) -> List[Dict[str, Any]]:
        """
        Build smart calendar mapping presets, overrides, and logged exercises.
        """
        # 1. Fetch weekly presets
        presets_query = select(WeeklyPreset)
        presets_result = await self.db.execute(presets_query)
        presets = {p.day_of_week: p.routine_tag for p in presets_result.scalars().all()}

        # 2. Fetch daily overrides in date range
        overrides_query = select(DailyOverride).where(
            and_(
                DailyOverride.workout_date >= start_date,
                DailyOverride.workout_date <= end_date
            )
        )
        overrides_result = await self.db.execute(overrides_query)
        overrides = {o.workout_date: o.routine_tag for o in overrides_result.scalars().all()}

        # 3. Fetch workout logs in date range
        logs_query = (
            select(DailyWorkoutLog)
            .where(
                and_(
                    DailyWorkoutLog.workout_date >= start_date,
                    DailyWorkoutLog.workout_date <= end_date
                )
            )
            .options(joinedload(DailyWorkoutLog.exercise))
            .order_by(DailyWorkoutLog.id.asc())
        )
        logs_result = await self.db.execute(logs_query)
        logs = logs_result.scalars().all()

        # Group workout logs by date
        logs_by_date: Dict[datetime.date, List[DailyWorkoutLog]] = {}
        for log in logs:
            if log.workout_date not in logs_by_date:
                logs_by_date[log.workout_date] = []
            logs_by_date[log.workout_date].append(log)

        # 4. Generate day by day calendar list
        events = []
        curr = start_date
        while curr <= end_date:
            db_weekday = self._get_db_weekday(curr)
            preset_tag = presets.get(db_weekday, "rest")
            
            # Check override
            is_override = curr in overrides
            routine_tag = overrides.get(curr, preset_tag)

            # Get logs
            day_logs = logs_by_date.get(curr, [])
            serialized_logs = []
            for l in day_logs:
                serialized_logs.append({
                    "id": l.id,
                    "exercise_id": l.exercise_id,
                    "is_completed": l.is_completed,
                    "tracking_data": l.tracking_data,
                    "exercise": {
                        "id": l.exercise.id,
                        "name_eng": l.exercise.name_eng,
                        "name_vie": l.exercise.name_vie,
                        "tracking_type": l.exercise.tracking_type,
                        "primary_muscle": l.exercise.primary_muscle,
                        "tags": l.exercise.tags
                    } if l.exercise else None
                })

            events.append({
                "date": curr.isoformat(),
                "day_of_week": db_weekday,
                "weekday_name": curr.strftime("%A"),
                "routine_tag": routine_tag,
                "preset_tag": preset_tag,
                "is_override": is_override,
                "workout_logs": serialized_logs
            })
            
            curr += datetime.timedelta(days=1)

        return events

    async def set_override(self, workout_date: datetime.date, routine_tag: Optional[str]) -> DailyOverride:
        """
        Add or update routine override for a specific date.
        If routine_tag is None or empty, delete the override (revert to preset).
        """
        if not routine_tag:
            # Delete override
            stmt = delete(DailyOverride).where(DailyOverride.workout_date == workout_date)
            await self.db.execute(stmt)
            await self.db.commit()
            return None

        # Upsert override using PostgreSQL upsert helper
        stmt = pg_insert(DailyOverride).values(
            workout_date=workout_date,
            routine_tag=routine_tag
        )
        stmt = stmt.on_conflict_do_update(
            constraint="daily_overrides_pkey",
            set_={"routine_tag": routine_tag}
        )
        await self.db.execute(stmt)
        await self.db.commit()

        # Retrieve and return
        query = select(DailyOverride).where(DailyOverride.workout_date == workout_date)
        result = await self.db.execute(query)
        return result.scalar_one()
