import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.app.database import init_db
from backend.app.routers import exercises, presets, workouts, calendar, stats

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (creates tables on boot using SQLAlchemy Base.metadata.create_all)
    await init_db()
    yield

app = FastAPI(title="Fitness OS API", lifespan=lifespan)

# Register routers
app.include_router(exercises.router)
app.include_router(presets.router)
app.include_router(workouts.router)
app.include_router(calendar.router)
app.include_router(stats.router)

# Resolve path to frontend folder (2 levels up from backend/app/main.py)
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
os.makedirs(frontend_dir, exist_ok=True)

# Mount frontend static directory
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
