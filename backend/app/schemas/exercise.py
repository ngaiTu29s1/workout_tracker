from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

class ExerciseBase(BaseModel):
    name_eng: str
    name_vie: Optional[str] = None
    instructions: Optional[str] = None
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    pro_tips: Optional[str] = None
    tracking_type: str  # WEIGHT_REPS, BODYWEIGHT_REPS, TIME
    primary_muscle: Optional[str] = None
    secondary_muscle: List[str] = []
    tags: List[str] = []

class ExerciseCreate(ExerciseBase):
    pass

class ExerciseUpdate(BaseModel):
    name_eng: Optional[str] = None
    name_vie: Optional[str] = None
    instructions: Optional[str] = None
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    pro_tips: Optional[str] = None
    tracking_type: Optional[str] = None
    primary_muscle: Optional[str] = None
    secondary_muscle: Optional[List[str]] = None
    tags: Optional[List[str]] = None

class ExerciseResponse(ExerciseBase):
    id: int
    created_at: datetime
    pool_id: Optional[int] = None
    pool_image: Optional[str] = None
    pool_gif: Optional[str] = None

    class Config:
        from_attributes = True
