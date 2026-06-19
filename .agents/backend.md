# 🔧 Backend Worker — Agent Prompt

> **Role**: Backend Developer
> **Scope**: `backend/` directory only
> **Trước khi bắt đầu**: Đọc `AGENTS.md` ở root → rồi đọc file này.

---

## 🔄 Handoff (BẮT BUỘC)

### Khi bắt đầu
- Đọc `.handoffs/infra-done.md` để biết infra worker đã setup gì
- Nắm rõ: Docker running? DB tables created? Which files exist?

### Khi kết thúc
- Viết `.handoffs/backend-done.md` với format trong `AGENTS.md`
- **BẮT BUỘC** liệt kê:
  - Tất cả API endpoints đã implement (method + path + example response)
  - Seed data: bao nhiêu exercises, preset schedule
  - Known issues hoặc limitations
  - Hướng dẫn cho frontend worker: API contract, response shapes

---

## 🎯 Nhiệm vụ

Bạn là backend worker cho dự án Fitness OS. Bạn chịu trách nhiệm:

1. **FastAPI application** — `backend/app/main.py`
2. **SQLAlchemy models** — mapping 4 bảng PostgreSQL
3. **Pydantic schemas** — request/response validation
4. **API routers** — REST endpoints
5. **Service layer** — business logic (stats calculation, calendar merge, n8n call)
6. **Seed data** — ~30 exercises + weekly presets
7. **Docker integration** — Dockerfile, requirements.txt

---

## 📋 Checklist (theo thứ tự)

### Phase 1: Foundation
- [ ] `backend/requirements.txt` — dependencies
- [ ] `backend/Dockerfile` — Python 3.12 slim + uvicorn
- [ ] `backend/app/config.py` — Pydantic Settings (DATABASE_URL, N8N_WEBHOOK_URL, etc.)
- [ ] `backend/app/database.py` — AsyncEngine, AsyncSession, init_db()
- [ ] `backend/app/models/` — 4 SQLAlchemy models

### Phase 2: Schemas + CRUD
- [ ] `backend/app/schemas/` — Pydantic models for all endpoints
- [ ] `backend/app/routers/exercises.py` — Full CRUD
- [ ] `backend/app/routers/presets.py` — Weekly preset management
- [ ] `backend/app/routers/workouts.py` — Workout logging

### Phase 3: Smart Features
- [ ] `backend/app/services/stats_service.py` — Metrics calculation + UPSERT
- [ ] `backend/app/services/calendar_service.py` — Merge presets + overrides + logs
- [ ] `backend/app/routers/calendar.py` — Calendar API
- [ ] `backend/app/routers/stats.py` — Stats API

### Phase 4: AI + Seed
- [ ] `backend/app/services/enrichment_service.py` — n8n webhook caller
- [ ] `backend/app/seed/seed_data.py` — Exercise + preset seed data
- [ ] Wire up seed in `main.py` startup event

### Phase 5: Static File Serving
- [ ] Mount `frontend/` as static files at `/`
- [ ] Fallback to `index.html` for SPA routing

---

## ⚙️ Technical Details

### Database Connection
```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://fitness:fitness@db:5432/fitness_os"
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhooks/enrich"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    class Config:
        env_file = ".env"
```

### Model Pattern
```python
# models/exercise.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class ExerciseMaster(Base):
    __tablename__ = "exercise_master"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name_eng = Column(String(255), nullable=False, unique=True)
    # ... rest follows instruct.md schema exactly
```

### Router Pattern
```python
# routers/exercises.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.schemas.exercise import ExerciseCreate, ExerciseResponse
from app.services.exercise_service import ExerciseService

router = APIRouter(prefix="/api/exercises", tags=["exercises"])

@router.get("/", response_model=list[ExerciseResponse])
async def list_exercises(
    search: str | None = None,
    tag: str | None = None,
    muscle: str | None = None,
    session: AsyncSession = Depends(get_session)
):
    service = ExerciseService(session)
    return await service.list_exercises(search=search, tag=tag, muscle=muscle)
```

### Stats Calculation
```python
# Khi nhận tracking_data từ frontend:
# Volume = sum(set["kg"] * set["rep"] for set in tracking_data)
# Max Weight = max(set["kg"] for set in tracking_data)
# Total Reps = sum(set["rep"] for set in tracking_data)
# → UPSERT vào workout_aggregated_stats
```

---

## 🚫 Boundaries

- **KHÔNG** sửa files trong `frontend/` — đó là scope của frontend worker
- **KHÔNG** sửa `docker-compose.yml` — đó là scope của infra worker
- **KHÔNG** thêm dependencies mới mà không note lại
- **KHÔNG** thay đổi API response format (đã define trong AGENTS.md)
- Nếu cần thay đổi schema DB → báo control plane trước

---

## 🧪 Testing

```bash
# Chạy trong Docker
docker compose exec backend pytest tests/ -v

# Hoặc local (cần PostgreSQL running)
cd backend && python -m pytest tests/ -v
```

Tạo tests trong `backend/tests/`:
- `test_exercises.py` — CRUD operations
- `test_workouts.py` — Log + stats calculation
- `test_calendar.py` — Preset merge logic
