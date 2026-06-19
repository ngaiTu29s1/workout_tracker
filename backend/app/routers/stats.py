from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database import get_db

router = APIRouter(prefix="/api/stats", tags=["Stats"])

@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)):
    return {"data": [], "message": "Success", "status": "ok"}
