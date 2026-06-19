from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database import get_db

router = APIRouter(prefix="/api/calendar", tags=["Calendar"])

@router.get("")
async def get_calendar(db: AsyncSession = Depends(get_db)):
    return {"data": [], "message": "Success", "status": "ok"}
