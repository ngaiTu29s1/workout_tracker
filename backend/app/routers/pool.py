from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.app.database import get_db
from backend.app.services.pool_service import PoolService

router = APIRouter(prefix="/api/pool", tags=["Pool"])

@router.get("/search")
async def search_pool(
    q: Optional[str] = "",
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    service = PoolService(db)
    results = await service.search(q, limit)
    return {
        "data": results,
        "message": "Pool search completed successfully",
        "status": "ok"
    }

@router.get("/categories")
async def get_pool_categories(db: AsyncSession = Depends(get_db)):
    service = PoolService(db)
    categories = await service.get_categories()
    return {
        "data": categories,
        "message": "Categories retrieved successfully",
        "status": "ok"
    }

@router.get("/{id}")
async def get_pool_detail(id: int, db: AsyncSession = Depends(get_db)):
    service = PoolService(db)
    detail = await service.get_by_id(id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise Pool item with ID {id} not found"
        )
    return {
        "data": detail,
        "message": "Pool detail retrieved successfully",
        "status": "ok"
    }
