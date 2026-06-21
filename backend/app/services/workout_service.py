import datetime
import httpx
import logging
from datetime import timedelta
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import settings
from backend.app.models.exercise import ExerciseMaster
from backend.app.models.workout_log import DailyWorkoutLog
from backend.app.schemas.workout import WorkoutLogCreate, WorkoutLogUpdate
from backend.app.services.stats_service import StatsService

logger = logging.getLogger(__name__)

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

    async def get_ai_suggestions(self, workout_date: datetime.date, routine_tag: str) -> List[dict]:
        """
        Fetch 14-day history and available exercises to trigger AI suggest via n8n.
        Does not fall back to local logic.
        """
        # Fetch completed logs for the last 14 days
        start_date = workout_date - timedelta(days=14)
        query_logs = (
            select(DailyWorkoutLog)
            .where(
                and_(
                    DailyWorkoutLog.workout_date >= start_date,
                    DailyWorkoutLog.workout_date < workout_date,
                    DailyWorkoutLog.is_completed == True
                )
            )
            .options(joinedload(DailyWorkoutLog.exercise))
            .order_by(DailyWorkoutLog.workout_date.desc())
        )
        res_logs = await self.db.execute(query_logs)
        logs = list(res_logs.scalars().all())

        # Format history
        history_data = []
        for log in logs:
            history_data.append({
                "date": log.workout_date.isoformat(),
                "exercise_name": log.exercise.name_eng,
                "sets": [
                    {
                        "set": s.get("set"),
                        "kg": s.get("kg"),
                        "rep": s.get("rep"),
                        "time_seconds": s.get("time_seconds")
                    } for s in log.tracking_data
                ]
            })

        # Fetch personal exercises pool for tag
        query_exercises = select(ExerciseMaster).where(
            ExerciseMaster.tags.contains([routine_tag])
        )
        res_exercises = await self.db.execute(query_exercises)
        exercises = list(res_exercises.scalars().all())

        exercises_pool = []
        for ex in exercises:
            exercises_pool.append({
                "id": ex.id,
                "name_eng": ex.name_eng,
                "primary_muscle": ex.primary_muscle,
                "secondary_muscle": ex.secondary_muscle,
                "tracking_type": ex.tracking_type
            })

        payload = {
            "action": "suggest",
            "date": workout_date.isoformat(),
            "routine_tag": routine_tag,
            "history_14d": history_data,
            "exercises_pool": exercises_pool
        }

        if not settings.N8N_AUTOFILL_WEBHOOK_URL or any(p in settings.N8N_AUTOFILL_WEBHOOK_URL.lower() for p in ["change_me", "placeholder", "local"]):
            raise ValueError("N8N Webhook not configured")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.N8N_AUTOFILL_WEBHOOK_URL,
                    json=payload,
                    timeout=30.0
                )
                if response.status_code != 200:
                    raise ValueError(f"N8N Webhook returned status code {response.status_code}")
                
                res_json = response.json()
                return self._parse_n8n_response(res_json)
        except Exception as e:
            logger.error(f"Failed to connect to n8n suggest webhook: {e}")
            raise ValueError(f"Failed to connect to n8n suggest webhook: {str(e)}")

    async def get_local_suggestions(self, workout_date: datetime.date, routine_tag: str) -> List[dict]:
        """
        Fetch exercises and history locally and generate local suggestions.
        """
        # Fetch completed logs for the last 14 days
        start_date = workout_date - timedelta(days=14)
        query_logs = (
            select(DailyWorkoutLog)
            .where(
                and_(
                    DailyWorkoutLog.workout_date >= start_date,
                    DailyWorkoutLog.workout_date < workout_date,
                    DailyWorkoutLog.is_completed == True
                )
            )
            .options(joinedload(DailyWorkoutLog.exercise))
            .order_by(DailyWorkoutLog.workout_date.desc())
        )
        res_logs = await self.db.execute(query_logs)
        logs = list(res_logs.scalars().all())

        # Fetch personal exercises pool for tag
        query_exercises = select(ExerciseMaster).where(
            ExerciseMaster.tags.contains([routine_tag])
        )
        res_exercises = await self.db.execute(query_exercises)
        exercises = list(res_exercises.scalars().all())

        return await self._generate_fallback_suggestions(exercises, logs)

    async def _generate_fallback_suggestions(self, exercises: List[ExerciseMaster], logs: List[DailyWorkoutLog]) -> List[dict]:
        # Pick first 6 exercises as a fallback
        selected_exercises = exercises[:6]
        suggestions = []
        for ex in selected_exercises:
            suggestions.append(await self._get_fallback_single_suggestion(ex, logs))
        return suggestions

    async def _get_fallback_single_suggestion(self, exercise: ExerciseMaster, logs: List[DailyWorkoutLog]) -> dict:
        # Find most recent log for this exercise
        last_log = None
        for log in logs:
            if log.exercise_id == exercise.id:
                last_log = log
                break

        suggested_sets = []
        if last_log and last_log.tracking_data:
            for s in last_log.tracking_data:
                kg = s.get("kg")
                rep = s.get("rep")
                time_seconds = s.get("time_seconds")
                if kg is not None and kg > 0:
                    # Apply a light progressive overload (+2.5kg)
                    kg = kg + 2.5
                elif rep is not None and rep > 0:
                    rep = rep + 1
                suggested_sets.append({
                    "set": s.get("set"),
                    "kg": kg,
                    "rep": rep,
                    "time_seconds": time_seconds
                })
        else:
            # If no history, suggest 3 sets but leave kg/rep/time_seconds as None (blank)
            for set_num in range(1, 4):
                suggested_sets.append({
                    "set": set_num,
                    "kg": None,
                    "rep": None,
                    "time_seconds": None
                })
        
        return {
            "exercise_id": exercise.id,
            "suggested_sets": suggested_sets
        }

    async def swap_ai_suggestion(self, workout_date: datetime.date, routine_tag: str, exercise_id: int, current_suggestions: List[int]) -> dict:
        """
        Replace a single exercise suggestion with another exercise targeting the same primary muscle,
        excluding exercises already in current_suggestions, calling n8n webhook.
        """
        # Fetch the original exercise
        original_ex = await self.db.get(ExerciseMaster, exercise_id)
        if not original_ex:
            raise ValueError(f"Exercise with ID {exercise_id} not found.")

        # Find candidates: same tag, same primary muscle, not in current_suggestions, and not itself
        query_candidates = select(ExerciseMaster).where(
            and_(
                ExerciseMaster.tags.contains([routine_tag]),
                ExerciseMaster.primary_muscle.ilike(original_ex.primary_muscle),
                ~ExerciseMaster.id.in_(current_suggestions),
                ExerciseMaster.id != exercise_id
            )
        )
        res_candidates = await self.db.execute(query_candidates)
        candidates = list(res_candidates.scalars().all())

        # If no same-muscle candidate, fallback to any other exercise with same tag
        if not candidates:
            query_any_candidates = select(ExerciseMaster).where(
                and_(
                    ExerciseMaster.tags.contains([routine_tag]),
                    ~ExerciseMaster.id.in_(current_suggestions),
                    ExerciseMaster.id != exercise_id
                )
            )
            res_any = await self.db.execute(query_any_candidates)
            candidates = list(res_any.scalars().all())

        if not candidates:
            # Nothing else to swap to
            return {
                "exercise_id": original_ex.id,
                "suggested_sets": []
            }

        # Format history
        start_date = workout_date - timedelta(days=14)
        query_logs = (
            select(DailyWorkoutLog)
            .where(
                and_(
                    DailyWorkoutLog.workout_date >= start_date,
                    DailyWorkoutLog.workout_date < workout_date,
                    DailyWorkoutLog.is_completed == True
                )
            )
            .options(joinedload(DailyWorkoutLog.exercise))
        )
        res_logs = await self.db.execute(query_logs)
        logs = list(res_logs.scalars().all())

        history_data = []
        for log in logs:
            history_data.append({
                "date": log.workout_date.isoformat(),
                "exercise_name": log.exercise.name_eng,
                "sets": [
                    {
                        "set": s.get("set"),
                        "kg": s.get("kg"),
                        "rep": s.get("rep"),
                        "time_seconds": s.get("time_seconds")
                    } for s in log.tracking_data
                ]
            })

        exercises_pool = []
        for ex in candidates:
            exercises_pool.append({
                "id": ex.id,
                "name_eng": ex.name_eng,
                "primary_muscle": ex.primary_muscle,
                "secondary_muscle": ex.secondary_muscle,
                "tracking_type": ex.tracking_type
            })

        payload = {
            "action": "swap",
            "date": workout_date.isoformat(),
            "routine_tag": routine_tag,
            "exercise_id_to_swap": exercise_id,
            "history_14d": history_data,
            "exercises_pool": exercises_pool
        }

        if not settings.N8N_AUTOFILL_WEBHOOK_URL or any(p in settings.N8N_AUTOFILL_WEBHOOK_URL.lower() for p in ["change_me", "placeholder", "local"]):
            raise ValueError("N8N Webhook not configured")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.N8N_AUTOFILL_WEBHOOK_URL,
                    json=payload,
                    timeout=30.0
                )
                if response.status_code != 200:
                    raise ValueError(f"N8N Webhook returned status code {response.status_code}")
                
                res_json = response.json()
                return self._parse_n8n_swap_response(res_json)
        except Exception as e:
            logger.error(f"Failed to connect to n8n swap webhook: {e}")
            raise ValueError(f"Failed to connect to n8n swap webhook: {str(e)}")

    async def swap_local_suggestion(self, workout_date: datetime.date, routine_tag: str, exercise_id: int, current_suggestions: List[int]) -> dict:
        """
        Replace a single exercise suggestion with another exercise targeting the same primary muscle,
        excluding exercises already in current_suggestions, using local DB logic.
        """
        # Fetch the original exercise
        original_ex = await self.db.get(ExerciseMaster, exercise_id)
        if not original_ex:
            raise ValueError(f"Exercise with ID {exercise_id} not found.")

        # Find candidates: same tag, same primary muscle, not in current_suggestions, and not itself
        query_candidates = select(ExerciseMaster).where(
            and_(
                ExerciseMaster.tags.contains([routine_tag]),
                ExerciseMaster.primary_muscle.ilike(original_ex.primary_muscle),
                ~ExerciseMaster.id.in_(current_suggestions),
                ExerciseMaster.id != exercise_id
            )
        )
        res_candidates = await self.db.execute(query_candidates)
        candidates = list(res_candidates.scalars().all())

        # If no same-muscle candidate, fallback to any other exercise with same tag
        if not candidates:
            query_any_candidates = select(ExerciseMaster).where(
                and_(
                    ExerciseMaster.tags.contains([routine_tag]),
                    ~ExerciseMaster.id.in_(current_suggestions),
                    ExerciseMaster.id != exercise_id
                )
            )
            res_any = await self.db.execute(query_any_candidates)
            candidates = list(res_any.scalars().all())

        if not candidates:
            # Nothing else to swap to
            return {
                "exercise_id": original_ex.id,
                "suggested_sets": []
            }

        # Fetch logs for history overload
        start_date = workout_date - timedelta(days=14)
        query_logs = (
            select(DailyWorkoutLog)
            .where(
                and_(
                    DailyWorkoutLog.workout_date >= start_date,
                    DailyWorkoutLog.workout_date < workout_date,
                    DailyWorkoutLog.is_completed == True
                )
            )
            .options(joinedload(DailyWorkoutLog.exercise))
        )
        res_logs = await self.db.execute(query_logs)
        logs = list(res_logs.scalars().all())

        chosen_ex = candidates[0]
        replacement = await self._get_fallback_single_suggestion(chosen_ex, logs)
        return replacement

    async def apply_suggestions(self, workout_date: datetime.date, suggestions: List[dict]) -> List[DailyWorkoutLog]:
        """
        Apply suggestions by saving logs to the DB. Alias to apply_ai_suggestions.
        """
        return await self.apply_ai_suggestions(workout_date, suggestions)

    async def apply_ai_suggestions(self, workout_date: datetime.date, suggestions: List[dict]) -> List[DailyWorkoutLog]:
        """
        Apply suggestions by saving logs to the DB with pre-filled sets (not completed).
        """
        logs_created = []
        for sugg in suggestions:
            ex_id = sugg["exercise_id"]
            sets = sugg.get("suggested_sets", [])
            
            # Format Pydantic-compatible sets
            formatted_sets = []
            for i, s in enumerate(sets):
                formatted_sets.append({
                    "set": s.get("set") or (i + 1),
                    "kg": s.get("kg"),
                    "rep": s.get("rep"),
                    "time_seconds": s.get("time_seconds")
                })

            # Check if log already exists
            query = select(DailyWorkoutLog).where(
                and_(
                    DailyWorkoutLog.workout_date == workout_date,
                    DailyWorkoutLog.exercise_id == ex_id
                )
            )
            result = await self.db.execute(query)
            db_log = result.scalar_one_or_none()

            if db_log:
                db_log.tracking_data = formatted_sets
            else:
                db_log = DailyWorkoutLog(
                    workout_date=workout_date,
                    exercise_id=ex_id,
                    tracking_data=formatted_sets,
                    is_completed=False
                )
                self.db.add(db_log)
            
            logs_created.append(db_log)

        await self.db.commit()

        # Recalculate stats for each log
        stats_svc = StatsService(self.db)
        for log in logs_created:
            await self.db.refresh(log)
            await stats_svc.calculate_metrics(log.id)

        # Refresh with joins
        completed_logs = []
        for log in logs_created:
            completed_log = await self.get_workout_log_by_id(log.id)
            if completed_log:
                completed_logs.append(completed_log)

        return completed_logs

    def _parse_n8n_response(self, res_json) -> List[dict]:
        import json
        if isinstance(res_json, list):
            return res_json
        
        if isinstance(res_json, dict):
            if "suggestions" in res_json:
                return res_json["suggestions"]
            
            # Check for OpenAI-style response format
            if "choices" in res_json and len(res_json["choices"]) > 0:
                choice = res_json["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
                    # Clean markdown code blocks if LLM returned them
                    content = content.replace("```json", "").replace("```", "").strip()
                    try:
                        parsed = json.loads(content)
                        return self._parse_n8n_response(parsed)
                    except Exception as e:
                        logger.error(f"Failed to parse OpenAI message content: {e}")
                        
        return []

    def _parse_n8n_swap_response(self, res_json) -> dict:
        import json
        if isinstance(res_json, list) and len(res_json) > 0:
            return res_json[0]
        
        if isinstance(res_json, dict):
            # Check for OpenAI-style response format
            if "choices" in res_json and len(res_json["choices"]) > 0:
                choice = res_json["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
                    content = content.replace("```json", "").replace("```", "").strip()
                    try:
                        parsed = json.loads(content)
                        return self._parse_n8n_swap_response(parsed)
                    except Exception as e:
                        logger.error(f"Failed to parse OpenAI swap message content: {e}")
            return res_json
        
        raise ValueError("N8N Webhook returned empty or invalid response")
