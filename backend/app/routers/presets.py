from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from backend.app.database import get_db
from backend.app.models.preset import WeeklyPreset
from backend.app.schemas.preset import WeeklyPresetUpdate, BulkWeeklyPresetUpdate

router = APIRouter(prefix="/api/presets", tags=["Presets"])

@router.get("")
async def get_presets(db: AsyncSession = Depends(get_db)):
    query = select(WeeklyPreset).order_by(WeeklyPreset.day_of_week.asc())
    result = await db.execute(query)
    presets = result.scalars().all()
    
    # If the DB is empty (not seeded yet), we can return an empty list or default values.
    # We will seed on startup, so it should be populated.
    return {
        "data": presets,
        "message": "Weekly presets retrieved successfully",
        "status": "ok"
    }

@router.put("/{day}")
async def update_preset(day: int, schema: WeeklyPresetUpdate, db: AsyncSession = Depends(get_db)):
    if day < 1 or day > 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Day of week must be between 1 (Sunday) and 7 (Saturday)"
        )
    
    query = select(WeeklyPreset).where(WeeklyPreset.day_of_week == day)
    result = await db.execute(query)
    preset = result.scalar_one_or_none()
    
    if not preset:
        preset = WeeklyPreset(day_of_week=day, routine_tag=schema.routine_tag)
        db.add(preset)
    else:
        preset.routine_tag = schema.routine_tag
        
    await db.commit()
    await db.refresh(preset)
    
    return {
        "data": preset,
        "message": f"Preset for day {day} updated successfully",
        "status": "ok"
    }

@router.put("")
async def bulk_update_presets(schema: BulkWeeklyPresetUpdate, db: AsyncSession = Depends(get_db)):
    updated_presets = []
    
    for p in schema.presets:
        if p.day_of_week < 1 or p.day_of_week > 7:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid day_of_week {p.day_of_week}. Must be between 1 and 7"
            )
            
        query = select(WeeklyPreset).where(WeeklyPreset.day_of_week == p.day_of_week)
        result = await db.execute(query)
        preset = result.scalar_one_or_none()
        
        if not preset:
            preset = WeeklyPreset(day_of_week=p.day_of_week, routine_tag=p.routine_tag)
            db.add(preset)
        else:
            preset.routine_tag = p.routine_tag
            
        updated_presets.append(preset)
        
    await db.commit()
    for up in updated_presets:
        await db.refresh(up)
        
    # Sort updated presets by day_of_week
    updated_presets.sort(key=lambda x: x.day_of_week)
    
    return {
        "data": updated_presets,
        "message": "Weekly presets bulk updated successfully",
        "status": "ok"
    }
