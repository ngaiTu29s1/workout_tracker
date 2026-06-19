from pydantic import BaseModel, Field
from typing import Optional, List

class WeeklyPresetBase(BaseModel):
    day_of_week: int = Field(..., ge=1, le=7)  # 1 = Sunday, 2 = Monday, etc.
    routine_tag: Optional[str] = None  # e.g., push, pull, leg, rest

class WeeklyPresetUpdate(BaseModel):
    routine_tag: Optional[str] = None

class BulkWeeklyPresetUpdate(BaseModel):
    presets: List[WeeklyPresetBase]

class WeeklyPresetResponse(WeeklyPresetBase):
    class Config:
        from_attributes = True
