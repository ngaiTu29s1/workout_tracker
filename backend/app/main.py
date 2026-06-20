import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.database import init_db, async_session_maker
from backend.app.routers import exercises, presets, workouts, calendar, stats, pool
from backend.app.seed import seed_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skip DB init and seeding if running in test environment
    if os.getenv("TESTING") == "True":
        logger.info("Test environment detected. Skipping DB init and seeding in lifespan.")
    else:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Checking seed data...")
        async with async_session_maker() as session:
            await seed_db(session)
    yield

app = FastAPI(title="Fitness OS API", lifespan=lifespan)

# Exception handler for Starlette/FastAPI HTTPExceptions
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status": "error"
        }
    )

# Exception handler for request validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "status": "error"
        }
    )

# Register routers
app.include_router(exercises)
app.include_router(presets)
app.include_router(workouts)
app.include_router(calendar)
app.include_router(stats)
app.include_router(pool)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# Resolve path to frontend folder (2 levels up from backend/app/main.py)
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
os.makedirs(frontend_dir, exist_ok=True)

# Mount exercise pool static directory if configured
pool_data_path = os.getenv("POOL_DATA_PATH")
if pool_data_path:
    os.makedirs(pool_data_path, exist_ok=True)
    app.mount("/pool", StaticFiles(directory=pool_data_path), name="pool")

# Mount frontend static directory
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
