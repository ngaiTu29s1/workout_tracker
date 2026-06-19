from datetime import date
from typing import List
from sqlalchemy import Date, ForeignKey, Boolean, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base

class DailyWorkoutLog(Base):
    __tablename__ = "daily_workout_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workout_date: Mapped[date] = mapped_column(Date, default=func.current_date(), server_default=func.current_date())
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercise_master.id", ondelete="CASCADE"), nullable=False)
    tracking_data: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    # Relationships
    exercise: Mapped["ExerciseMaster"] = relationship("ExerciseMaster", back_populates="logs")
    stats: Mapped[List["WorkoutAggregatedStats"]] = relationship("WorkoutAggregatedStats", back_populates="log", cascade="all, delete-orphan")
