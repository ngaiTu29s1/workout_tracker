from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import date

class WorkoutSet(BaseModel):
    set: int
    kg: Optional[float] = None
    rep: Optional[int] = None
    time_seconds: Optional[int] = None # For TIME type if needed

class WorkoutLogBase(BaseModel):
    workout_date: date
    exercise_id: int
    tracking_data: List[Dict[str, Any]] = []
    is_completed: bool = False

class WorkoutLogCreate(WorkoutLogBase):
    pass

class WorkoutLogResponse(WorkoutLogBase):
    id: int

    class Config:
        from_attributes = True
