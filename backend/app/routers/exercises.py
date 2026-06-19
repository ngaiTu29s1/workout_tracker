from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database import get_db

router = APIRouter(prefix="/api/exercises", tags=["Exercises"])

@router.get("")
async def get_exercises(db: AsyncSession = Depends(get_db)):
    return {"data": [], "message": "Success", "status": "ok"}
