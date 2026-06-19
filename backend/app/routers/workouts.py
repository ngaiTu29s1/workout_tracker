from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import datetime
from typing import Optional

from backend.app.database import get_db
from backend.app.schemas.workout import WorkoutLogCreate, WorkoutLogUpdate
from backend.app.services.workout_service import WorkoutService

router = APIRouter(prefix="/api/workouts", tags=["Workouts"])

@router.get("")
async def get_workout_log_by_date(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
):
    # Default to today's date if not provided
    if not date:
        workout_date = datetime.date.today()
    else:
        try:
            workout_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date must be in YYYY-MM-DD format"
            )

    service = WorkoutService(db)
    logs = await service.get_workout_logs_by_date(workout_date)
    return {
        "data": logs,
        "message": "Workout logs retrieved successfully",
        "status": "ok"
    }

@router.post("")
async def log_workout(schema: WorkoutLogCreate, db: AsyncSession = Depends(get_db)):
    service = WorkoutService(db)
    log = await service.log_workout(schema)
    return {
        "data": log,
        "message": "Workout log saved successfully",
        "status": "ok"
    }

@router.put("/{id}")
async def update_workout_log(id: int, schema: WorkoutLogUpdate, db: AsyncSession = Depends(get_db)):
    service = WorkoutService(db)
    log = await service.update_workout_log(id, schema)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout log with ID {id} not found"
        )
    return {
        "data": log,
        "message": "Workout log updated successfully",
        "status": "ok"
    }

@router.delete("/{id}")
async def delete_workout_log(id: int, db: AsyncSession = Depends(get_db)):
    service = WorkoutService(db)
    success = await service.delete_workout_log(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout log with ID {id} not found"
        )
    return {
        "data": {"id": id},
        "message": "Workout log deleted successfully",
        "status": "ok"
    }

@router.post("/{id}/complete")
async def complete_workout_log(
    id: int,
    completed: bool = Query(True, description="Whether the exercise is completed"),
    db: AsyncSession = Depends(get_db)
):
    service = WorkoutService(db)
    log = await service.complete_workout_log(id, completed)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workout log with ID {id} not found"
        )
    return {
        "data": log,
        "message": f"Workout log status marked as {'completed' if completed else 'incomplete'} successfully",
        "status": "ok"
    }
