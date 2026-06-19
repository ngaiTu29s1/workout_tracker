from pydantic import BaseModel
from typing import Optional
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
