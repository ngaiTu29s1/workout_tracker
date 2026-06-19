from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database import Base

class WeeklyPreset(Base):
    __tablename__ = "weekly_presets"

    day_of_week: Mapped[int] = mapped_column(Integer, primary_key=True)  # 1 = Sunday, 2 = Monday, etc.
    routine_tag: Mapped[str] = mapped_column(String(50), nullable=True)  # e.g., push, pull, leg, rest
