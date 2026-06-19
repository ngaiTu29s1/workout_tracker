import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, and_, delete, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.models.workout_log import DailyWorkoutLog
from backend.app.models.exercise import ExerciseMaster
from backend.app.models.stats import WorkoutAggregatedStats
from backend.app.schemas.stats import ExerciseMetricHistoryPoint, OverviewStatsResponse, ExerciseStatsResponse

class StatsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_metrics(self, log_id: int) -> None:
        """
        Recalculate metrics for a given DailyWorkoutLog entry and UPSERT them into
        workout_aggregated_stats.
        """
        # Fetch the workout log and its exercise
        query = select(DailyWorkoutLog).where(DailyWorkoutLog.id == log_id)
        result = await self.db.execute(query)
        log = result.scalar_one_or_none()
        if not log:
            return

        # Fetch exercise to get tracking_type
        query_ex = select(ExerciseMaster).where(ExerciseMaster.id == log.exercise_id)
        result_ex = await self.db.execute(query_ex)
        exercise = result_ex.scalar_one_or_none()
        if not exercise:
            return

        # If log is not completed or tracking_data is empty, we delete any existing stats
        if not log.is_completed or not log.tracking_data:
            stmt = delete(WorkoutAggregatedStats).where(WorkoutAggregatedStats.log_id == log.id)
            await self.db.execute(stmt)
            await self.db.commit()
            return

        # Initialize metrics
        volume = Decimal("0")
        max_weight = Decimal("0")
        total_reps = Decimal("0")
        total_time = Decimal("0")

        # Parse tracking data (list of dictionaries representing sets)
        has_weight_reps = False
        has_time = False

        for set_data in log.tracking_data:
            # We must handle both object-like or dict-like access
            kg = set_data.get("kg") if isinstance(set_data, dict) else getattr(set_data, "kg", None)
            rep = set_data.get("rep") if isinstance(set_data, dict) else getattr(set_data, "rep", None)
            time_seconds = set_data.get("time_seconds") if isinstance(set_data, dict) else getattr(set_data, "time_seconds", None)

            # Ensure numeric conversion safely
            kg_val = Decimal(str(kg)) if kg is not None else Decimal("0")
            rep_val = Decimal(str(rep)) if rep is not None else Decimal("0")
            time_val = Decimal(str(time_seconds)) if time_seconds is not None else Decimal("0")

            if kg_val > 0 and rep_val > 0:
                volume += kg_val * rep_val
                has_weight_reps = True
            
            if kg_val > max_weight:
                max_weight = kg_val
                has_weight_reps = True

            if rep_val > 0:
                total_reps += rep_val
                has_weight_reps = True

            if time_val > 0:
                total_time += time_val
                has_time = True

        metrics_to_upsert = []

        # Determine metric based on tracking_type
        if exercise.tracking_type in ("WEIGHT_REPS", "BODYWEIGHT_REPS"):
            metrics_to_upsert.append(("VOLUME", volume, "kg"))
            metrics_to_upsert.append(("MAX_WEIGHT", max_weight, "kg"))
            metrics_to_upsert.append(("TOTAL_REPS", total_reps, "rep"))
        elif exercise.tracking_type == "TIME":
            metrics_to_upsert.append(("TOTAL_TIME", total_time, "sec"))
        else:
            # Fallback based on whatever data was entered
            if has_weight_reps:
                metrics_to_upsert.append(("VOLUME", volume, "kg"))
                metrics_to_upsert.append(("MAX_WEIGHT", max_weight, "kg"))
                metrics_to_upsert.append(("TOTAL_REPS", total_reps, "rep"))
            if has_time:
                metrics_to_upsert.append(("TOTAL_TIME", total_time, "sec"))

        # Delete any metrics that are no longer valid for this log
        existing_types = [m[0] for m in metrics_to_upsert]
        delete_stmt = delete(WorkoutAggregatedStats).where(
            and_(
                WorkoutAggregatedStats.log_id == log.id,
                WorkoutAggregatedStats.metric_type.not_in(existing_types)
            )
        )
        await self.db.execute(delete_stmt)

        # Upsert new metrics
        for metric_type, val, unit in metrics_to_upsert:
            stmt = pg_insert(WorkoutAggregatedStats).values(
                exercise_id=log.exercise_id,
                log_id=log.id,
                date=log.workout_date,
                metric_type=metric_type,
                metric_value=val,
                unit=unit
            )
            stmt = stmt.on_conflict_do_update(
                constraint="unique_daily_exercise_metric",
                set_={
                    "metric_value": val,
                    "log_id": log.id
                }
            )
            await self.db.execute(stmt)

        await self.db.commit()

    async def get_exercise_stats(self, exercise_id: int, range_str: str = "30d") -> ExerciseStatsResponse:
        """
        Get daily aggregated stats for a specific exercise over a range (e.g. 30d, 90d).
        """
        days = 30
        if range_str.endswith("d"):
            try:
                days = int(range_str[:-1])
            except ValueError:
                pass

        start_date = datetime.date.today() - datetime.timedelta(days=days)

        query = select(WorkoutAggregatedStats).where(
            and_(
                WorkoutAggregatedStats.exercise_id == exercise_id,
                WorkoutAggregatedStats.date >= start_date
            )
        ).order_by(WorkoutAggregatedStats.date.asc())

        result = await self.db.execute(query)
        stats_rows = result.scalars().all()

        # Pivot rows by date in Python
        by_date: Dict[datetime.date, Dict[str, Any]] = {}
        for row in stats_rows:
            if row.date not in by_date:
                by_date[row.date] = {
                    "date": row.date,
                    "volume": 0.0,
                    "max_weight": 0.0,
                    "total_reps": 0,
                    "total_time": 0
                }
            
            val = float(row.metric_value)
            if row.metric_type == "VOLUME":
                by_date[row.date]["volume"] = val
            elif row.metric_type == "MAX_WEIGHT":
                by_date[row.date]["max_weight"] = val
            elif row.metric_type == "TOTAL_REPS":
                by_date[row.date]["total_reps"] = int(val)
            elif row.metric_type == "TOTAL_TIME":
                by_date[row.date]["total_time"] = int(val)

        history = [
            ExerciseMetricHistoryPoint(
                date=k,
                volume=v["volume"],
                max_weight=v["max_weight"],
                total_reps=v["total_reps"],
                total_time=v["total_time"]
            )
            for k, v in sorted(by_date.items())
        ]

        return ExerciseStatsResponse(exercise_id=exercise_id, history=history)

    async def get_overview_stats(self, range_str: str = "30d") -> OverviewStatsResponse:
        """
        Get overview metrics for dashboard.
        """
        days = 30
        if range_str.endswith("d"):
            try:
                days = int(range_str[:-1])
            except ValueError:
                pass

        start_date = datetime.date.today() - datetime.timedelta(days=days)

        # 1. Total volume & reps
        stats_query = select(WorkoutAggregatedStats).where(
            WorkoutAggregatedStats.date >= start_date
        )
        result = await self.db.execute(stats_query)
        stats_rows = result.scalars().all()

        total_volume = 0.0
        total_reps = 0
        for row in stats_rows:
            if row.metric_type == "VOLUME":
                total_volume += float(row.metric_value)
            elif row.metric_type == "TOTAL_REPS":
                total_reps += int(row.metric_value)

        # 2. Total active days & total logs
        log_query = select(
            func.count(DailyWorkoutLog.id).label("total_logs"),
            func.count(func.distinct(DailyWorkoutLog.workout_date)).label("active_days")
        ).where(
            DailyWorkoutLog.workout_date >= start_date
        )
        log_result = await self.db.execute(log_query)
        log_summary = log_result.first()
        total_workouts = log_summary.total_logs if log_summary and log_summary.total_logs else 0
        total_active_days = log_summary.active_days if log_summary and log_summary.active_days else 0

        # 3. Recent activity chart (grouped by date)
        activity_query = select(
            DailyWorkoutLog.workout_date,
            func.count(DailyWorkoutLog.id).label("total"),
            func.sum(case((DailyWorkoutLog.is_completed == True, 1), else_=0)).label("completed")
        ).where(
            DailyWorkoutLog.workout_date >= start_date
        ).group_by(DailyWorkoutLog.workout_date).order_by(DailyWorkoutLog.workout_date.desc())

        activity_result = await self.db.execute(activity_query)
        activity_rows = activity_result.all()

        recent_activity = []
        for r in activity_rows:
            recent_activity.append({
                "date": str(r.workout_date),
                "total": r.total,
                "completed": r.completed or 0
            })

        return OverviewStatsResponse(
            total_workouts=total_workouts,
            total_active_days=total_active_days,
            total_volume_kg=total_volume,
            total_reps=total_reps,
            recent_activity=recent_activity
        )
