from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import datetime
from pydantic import BaseModel
from typing import Optional

from backend.app.database import get_db
from backend.app.services.calendar_service import CalendarService

router = APIRouter(prefix="/api/calendar", tags=["Calendar"])

class OverrideRequest(BaseModel):
    workout_date: datetime.date
    routine_tag: Optional[str] = None  # e.g., push, pull, leg, rest. None to revert to preset.

@router.get("")
async def get_calendar(
    start: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
):
    # Default: last 7 days to next 7 days if start and end are not provided
    today = datetime.date.today()
    
    if start:
        try:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be in YYYY-MM-DD format"
            )
    else:
        start_date = today - datetime.timedelta(days=7)
        
    if end:
        try:
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be in YYYY-MM-DD format"
            )
    else:
        end_date = today + datetime.timedelta(days=7)

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date"
        )

    service = CalendarService(db)
    events = await service.get_calendar_events(start_date, end_date)
    return {
        "data": events,
        "message": "Calendar events retrieved successfully",
        "status": "ok"
    }

@router.post("/override")
async def set_override(schema: OverrideRequest, db: AsyncSession = Depends(get_db)):
    service = CalendarService(db)
    override = await service.set_override(schema.workout_date, schema.routine_tag)
    return {
        "data": override,
        "message": "Routine override updated successfully",
        "status": "ok"
    }
