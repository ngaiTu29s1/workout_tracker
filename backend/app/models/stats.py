from datetime import date
from decimal import Decimal
from sqlalchemy import Date, ForeignKey, String, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base

class WorkoutAggregatedStats(Base):
    __tablename__ = "workout_aggregated_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercise_master.id", ondelete="CASCADE"), nullable=False)
    log_id: Mapped[int] = mapped_column(ForeignKey("daily_workout_log.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # VOLUME, MAX_WEIGHT, TOTAL_REPS, TOTAL_TIME
    metric_value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # kg, rep, sec

    # Relationships
    exercise: Mapped["ExerciseMaster"] = relationship("ExerciseMaster", back_populates="stats")
    log: Mapped["DailyWorkoutLog"] = relationship("DailyWorkoutLog", back_populates="stats")

    # Constraints
    __table_args__ = (
        UniqueConstraint("date", "exercise_id", "metric_type", name="unique_daily_exercise_metric"),
    )
