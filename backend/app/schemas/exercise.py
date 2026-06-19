from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ExerciseBase(BaseModel):
    name_eng: str
    name_vie: Optional[str] = None
    instructions: Optional[str] = None
    video_url: Optional[str] = None
    image_url: Optional[str] = None
    pro_tips: Optional[str] = None
    tracking_type: str
    primary_muscle: Optional[str] = None
    secondary_muscle: List[str] = []
    tags: List[str] = []

class ExerciseCreate(ExerciseBase):
    pass

class ExerciseResponse(ExerciseBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
