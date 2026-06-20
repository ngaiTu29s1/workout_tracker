from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database import Base

class ExercisePool(Base):
    __tablename__ = "exercise_pool"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pool_id: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)  # "0001", "0002"
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)                  # English name
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)                # "chest", "back", "waist"
    body_part: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)               # same/similar to category
    equipment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)               # "barbell", "body weight", "machine"
    target: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)                  # target muscle ("abs", "pectorals")
    instructions_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)                # English instructions (full text)
    instructions_vi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)                # Vietnamese (batch translated, nullable)
    muscle_group: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)            # primary muscle
    secondary_muscles: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    image_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)              # "images/0001-xxx.jpg"
    gif_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)                # "videos/0001-xxx.gif"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=func.now())
