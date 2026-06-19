from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date
from decimal import Decimal

class StatsBase(BaseModel):
    exercise_id: int
    log_id: int
    date: date
    metric_type: str
    metric_value: Decimal
    unit: str

class StatsResponse(StatsBase):
    id: int

    class Config:
        from_attributes = True

class ExerciseMetricHistoryPoint(BaseModel):
    date: date
    volume: Optional[float] = None
    max_weight: Optional[float] = None
    total_reps: Optional[int] = None
    total_time: Optional[int] = None

class ExerciseStatsResponse(BaseModel):
    exercise_id: int
    history: List[ExerciseMetricHistoryPoint]

class OverviewStatsResponse(BaseModel):
    total_workouts: int
    total_active_days: int
    total_volume_kg: float
    total_reps: int
    recent_activity: List[Dict[str, Any]]  # lists dates and completed exercise counts
