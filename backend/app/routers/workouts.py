from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import datetime
from typing import Optional, List
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.schemas.workout import WorkoutLogCreate, WorkoutLogUpdate
from backend.app.services.workout_service import WorkoutService
from backend.app.config import settings

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

class AISuggestRequest(BaseModel):
    date: str
    routine_tag: str

class AISwapRequest(BaseModel):
    date: str
    routine_tag: str
    exercise_id: int
    current_suggestions: List[int]

class AISuggestionItem(BaseModel):
    exercise_id: int
    suggested_sets: List[dict] = []

class AIApplyRequest(BaseModel):
    date: str
    suggestions: List[AISuggestionItem]

def is_n8n_webhook_configured() -> bool:
    url = settings.N8N_AUTOFILL_WEBHOOK_URL
    if not url:
        return False
    url_lower = url.lower()
    for p in ["change_me", "placeholder", "local"]:
        if p in url_lower:
            return False
    return True

@router.post("/local-suggest")
async def get_local_suggestions(schema: AISuggestRequest, db: AsyncSession = Depends(get_db)):
    try:
        workout_date = datetime.datetime.strptime(schema.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date must be in YYYY-MM-DD format"
        )
    service = WorkoutService(db)
    suggestions = await service.get_local_suggestions(workout_date, schema.routine_tag)
    return {
        "data": suggestions,
        "message": "Local suggestions retrieved successfully",
        "status": "ok"
    }

@router.post("/ai-suggest")
async def get_ai_suggestions(schema: AISuggestRequest, db: AsyncSession = Depends(get_db)):
    if not is_n8n_webhook_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="N8N Webhook not configured"
        )
    try:
        workout_date = datetime.datetime.strptime(schema.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date must be in YYYY-MM-DD format"
        )
    service = WorkoutService(db)
    try:
        suggestions = await service.get_ai_suggestions(workout_date, schema.routine_tag)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    return {
        "data": suggestions,
        "message": "AI suggestions retrieved successfully",
        "status": "ok"
    }

@router.post("/local-swap")
async def swap_local_suggestion(schema: AISwapRequest, db: AsyncSession = Depends(get_db)):
    try:
        workout_date = datetime.datetime.strptime(schema.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date must be in YYYY-MM-DD format"
        )
    service = WorkoutService(db)
    try:
        replacement = await service.swap_local_suggestion(
            workout_date,
            schema.routine_tag,
            schema.exercise_id,
            schema.current_suggestions
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    return {
        "data": replacement,
        "message": "Local suggestion swapped successfully",
        "status": "ok"
    }

@router.post("/ai-swap")
async def swap_ai_suggestion(schema: AISwapRequest, db: AsyncSession = Depends(get_db)):
    if not is_n8n_webhook_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="N8N Webhook not configured"
        )
    try:
        workout_date = datetime.datetime.strptime(schema.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date must be in YYYY-MM-DD format"
        )
    service = WorkoutService(db)
    try:
        replacement = await service.swap_ai_suggestion(
            workout_date,
            schema.routine_tag,
            schema.exercise_id,
            schema.current_suggestions
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    return {
        "data": replacement,
        "message": "AI suggestion swapped successfully",
        "status": "ok"
    }

@router.post("/apply-suggestions")
async def apply_suggestions(schema: AIApplyRequest, db: AsyncSession = Depends(get_db)):
    try:
        workout_date = datetime.datetime.strptime(schema.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date must be in YYYY-MM-DD format"
        )
    service = WorkoutService(db)
    
    suggestions_list = []
    for item in schema.suggestions:
        suggestions_list.append({
            "exercise_id": item.exercise_id,
            "suggested_sets": item.suggested_sets
        })
        
    logs = await service.apply_suggestions(workout_date, suggestions_list)
    return {
        "data": logs,
        "message": "Suggestions applied successfully",
        "status": "ok"
    }

@router.post("/ai-apply")
async def apply_ai_suggestions(schema: AIApplyRequest, db: AsyncSession = Depends(get_db)):
    try:
        workout_date = datetime.datetime.strptime(schema.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date must be in YYYY-MM-DD format"
        )
    service = WorkoutService(db)
    
    suggestions_list = []
    for item in schema.suggestions:
        suggestions_list.append({
            "exercise_id": item.exercise_id,
            "suggested_sets": item.suggested_sets
        })
        
    logs = await service.apply_ai_suggestions(workout_date, suggestions_list)
    return {
        "data": logs,
        "message": "AI suggestions applied successfully",
        "status": "ok"
    }

@router.get("/suggest-sets")
async def get_single_exercise_suggestion(exercise_id: int, db: AsyncSession = Depends(get_db)):
    from backend.app.models.workout_log import DailyWorkoutLog
    from backend.app.models.exercise import ExerciseMaster
    from sqlalchemy import select, and_
    
    # Fetch most recent completed log for this exercise
    query = (
        select(DailyWorkoutLog)
        .where(
            and_(
                DailyWorkoutLog.exercise_id == exercise_id,
                DailyWorkoutLog.is_completed == True
            )
        )
        .order_by(DailyWorkoutLog.workout_date.desc())
        .limit(1)
    )
    res = await db.execute(query)
    last_log = res.scalar_one_or_none()
    
    # Fetch exercise master info to verify it exists
    ex = await db.get(ExerciseMaster, exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")
        
    suggested_sets = []
    if last_log and last_log.tracking_data:
        for s in last_log.tracking_data:
            kg = s.get("kg")
            rep = s.get("rep")
            time_seconds = s.get("time_seconds")
            if kg is not None and kg > 0:
                kg = kg + 2.5
            elif rep is not None and rep > 0:
                rep = rep + 1
            suggested_sets.append({
                "set": s.get("set"),
                "kg": kg,
                "rep": rep,
                "time_seconds": time_seconds
            })
    else:
        # Default 3 sets empty
        for set_num in range(1, 4):
            suggested_sets.append({
                "set": set_num,
                "kg": None,
                "rep": None,
                "time_seconds": None
            })
            
    return {
        "data": {
            "exercise_id": exercise_id,
            "suggested_sets": suggested_sets
        },
        "message": "Suggested sets retrieved successfully",
        "status": "ok"
    }
