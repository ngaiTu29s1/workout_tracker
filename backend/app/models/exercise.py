from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base

class ExerciseMaster(Base):
    __tablename__ = "exercise_master"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name_eng: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name_vie: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    pro_tips: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tracking_type: Mapped[str] = mapped_column(String(50), nullable=False)  # WEIGHT_REPS, BODYWEIGHT_REPS, TIME
    primary_muscle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    secondary_muscle: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    tags: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())

    # Relationships (resolved via forward references string)
    logs: Mapped[List["DailyWorkoutLog"]] = relationship("DailyWorkoutLog", back_populates="exercise", cascade="all, delete-orphan")
    stats: Mapped[List["WorkoutAggregatedStats"]] = relationship("WorkoutAggregatedStats", back_populates="exercise", cascade="all, delete-orphan")
