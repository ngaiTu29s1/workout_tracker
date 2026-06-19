import datetime
import logging
import httpx
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.models.preset import WeeklyPreset, DailyOverride
from backend.app.models.workout_log import DailyWorkoutLog
from backend.app.models.exercise import ExerciseMaster
from backend.app.config import settings

logger = logging.getLogger(__name__)


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

    async def autofill_workout(self, workout_date: datetime.date) -> List[DailyWorkoutLog]:
        """
        Trigger AI Autofill via n8n webhook.
        Determines the routine_tag for that day, sends it to n8n,
        receives a list of suggested exercise IDs, and logs them in DailyWorkoutLog.
        If n8n is unconfigured or offline, falls back to a smart mock.
        """
        # 1. Resolve routine_tag for the date
        db_weekday = self._get_db_weekday(workout_date)
        presets_query = select(WeeklyPreset).where(WeeklyPreset.day_of_week == db_weekday)
        presets_result = await self.db.execute(presets_query)
        preset = presets_result.scalar_one_or_none()
        preset_tag = preset.routine_tag if preset else "rest"

        override_query = select(DailyOverride).where(DailyOverride.workout_date == workout_date)
        override_result = await self.db.execute(override_query)
        override = override_result.scalar_one_or_none()
        routine_tag = override.routine_tag if override else preset_tag

        if not routine_tag or routine_tag == "rest":
            raise ValueError(f"Cannot autofill workouts for a rest day ({routine_tag}) on {workout_date}.")

        payload = {
            "workout_date": workout_date.isoformat(),
            "routine_tag": routine_tag
        }

        exercise_ids = []

        # 2. Try calling n8n autofill webhook
        if settings.N8N_AUTOFILL_WEBHOOK_URL and "change_me" not in settings.N8N_AUTOFILL_WEBHOOK_URL and "local" not in settings.N8N_AUTOFILL_WEBHOOK_URL:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        settings.N8N_AUTOFILL_WEBHOOK_URL,
                        json=payload,
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        # Allow response formats like {"exercise_ids": [...]} or a list directly
                        if isinstance(data, dict):
                            exercise_ids = data.get("exercise_ids", [])
                        elif isinstance(data, list):
                            exercise_ids = data
                        logger.info("Successfully received autofill exercise IDs from n8n.")
                    else:
                        logger.warning(f"n8n autofill returned status code {response.status_code}. Using mock fallback.")
            except Exception as e:
                logger.warning(f"Failed to connect to n8n autofill webhook at {settings.N8N_AUTOFILL_WEBHOOK_URL}: {e}. Using mock fallback.")

        # 3. Fallback: Find matching exercises from local DB containing the routine tag
        if not exercise_ids:
            logger.info("Using local mock fallback for autofill.")
            # For JSONB column `tags`, contains expects a list/array
            stmt = select(ExerciseMaster).where(ExerciseMaster.tags.contains([routine_tag])).limit(5)
            result = await self.db.execute(stmt)
            matched_exercises = result.scalars().all()
            exercise_ids = [ex.id for ex in matched_exercises]

        if not exercise_ids:
            return []

        # 4. Insert DailyWorkoutLog entries for each exercise_id
        created_logs = []
        for ex_id in exercise_ids:
            # Check if log already exists for this exercise on this date
            log_query = select(DailyWorkoutLog).where(
                and_(
                    DailyWorkoutLog.workout_date == workout_date,
                    DailyWorkoutLog.exercise_id == ex_id
                )
            )
            log_result = await self.db.execute(log_query)
            existing_log = log_result.scalar_one_or_none()

            if not existing_log:
                new_log = DailyWorkoutLog(
                    workout_date=workout_date,
                    exercise_id=ex_id,
                    tracking_data=[],
                    is_completed=False
                )
                self.db.add(new_log)
                created_logs.append(new_log)

        if created_logs:
            await self.db.commit()

        # 5. Retrieve all logs for this date (including previously existing ones) to return
        all_logs_query = (
            select(DailyWorkoutLog)
            .where(DailyWorkoutLog.workout_date == workout_date)
            .options(joinedload(DailyWorkoutLog.exercise))
            .order_by(DailyWorkoutLog.id.asc())
        )
        all_logs_result = await self.db.execute(all_logs_query)
        return all_logs_result.scalars().all()

