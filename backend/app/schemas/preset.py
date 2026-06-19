from pydantic import BaseModel
from typing import Optional

class WeeklyPresetBase(BaseModel):
    day_of_week: int
    routine_tag: Optional[str] = None

class WeeklyPresetUpdate(BaseModel):
    routine_tag: Optional[str] = None

class WeeklyPresetResponse(WeeklyPresetBase):
    class Config:
        from_attributes = True
