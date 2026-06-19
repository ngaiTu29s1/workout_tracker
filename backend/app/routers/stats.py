from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.app.database import get_db
from backend.app.services.stats_service import StatsService

router = APIRouter(prefix="/api/stats", tags=["Stats"])

@router.get("/exercise/{id}")
async def get_exercise_stats(
    id: int,
    range: str = Query("30d", description="Range of statistics, e.g., 30d, 90d"),
    db: AsyncSession = Depends(get_db)
):
    service = StatsService(db)
    stats_data = await service.get_exercise_stats(id, range)
    return {
        "data": stats_data,
        "message": f"Statistics for exercise {id} retrieved successfully",
        "status": "ok"
    }

@router.get("/overview")
async def get_overview_stats(
    range: str = Query("30d", description="Range of statistics, e.g., 30d, 90d"),
    db: AsyncSession = Depends(get_db)
):
    service = StatsService(db)
    overview_data = await service.get_overview_stats(range)
    return {
        "data": overview_data,
        "message": "Dashboard statistics retrieved successfully",
        "status": "ok"
    }
