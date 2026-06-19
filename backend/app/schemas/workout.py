from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from backend.app.schemas.exercise import ExerciseResponse

class WorkoutSet(BaseModel):
    set: int
    kg: Optional[float] = None
    rep: Optional[int] = None
    time_seconds: Optional[int] = None

class WorkoutLogBase(BaseModel):
    workout_date: date
    exercise_id: int
    tracking_data: List[WorkoutSet] = []
    is_completed: bool = False

class WorkoutLogCreate(WorkoutLogBase):
    pass

class WorkoutLogUpdate(BaseModel):
    workout_date: Optional[date] = None
    exercise_id: Optional[int] = None
    tracking_data: Optional[List[WorkoutSet]] = None
    is_completed: Optional[bool] = None

class WorkoutLogResponse(WorkoutLogBase):
    id: int
    exercise: Optional[ExerciseResponse] = None

    class Config:
        from_attributes = True
