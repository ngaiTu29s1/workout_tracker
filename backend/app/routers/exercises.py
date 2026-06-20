from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.app.database import get_db
from backend.app.schemas.exercise import ExerciseCreate, ExerciseUpdate, ExerciseResponse
from backend.app.schemas.pool import AddFromPoolRequest
from backend.app.services.exercise_service import ExerciseService
from backend.app.services.enrichment_service import EnrichmentService

router = APIRouter(prefix="/api/exercises", tags=["Exercises"])

@router.get("")
async def get_exercises(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    muscle: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    service = ExerciseService(db)
    exercises = await service.list_exercises(search=search, tag=tag, muscle=muscle)
    return {
        "data": [ExerciseResponse.model_validate(ex) for ex in exercises],
        "message": "Exercises retrieved successfully",
        "status": "ok"
    }

@router.get("/{id}")
async def get_exercise(id: int, db: AsyncSession = Depends(get_db)):
    service = ExerciseService(db)
    exercise = await service.get_exercise(id)
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with ID {id} not found"
        )
    return {
        "data": ExerciseResponse.model_validate(exercise),
        "message": "Exercise retrieved successfully",
        "status": "ok"
    }

@router.post("")
async def create_exercise(schema: ExerciseCreate, db: AsyncSession = Depends(get_db)):
    service = ExerciseService(db)
    exercise = await service.create_exercise(schema)
    return {
        "data": ExerciseResponse.model_validate(exercise),
        "message": "Exercise created successfully",
        "status": "ok"
    }

@router.put("/{id}")
async def update_exercise(id: int, schema: ExerciseUpdate, db: AsyncSession = Depends(get_db)):
    service = ExerciseService(db)
    exercise = await service.update_exercise(id, schema)
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with ID {id} not found"
        )
    return {
        "data": ExerciseResponse.model_validate(exercise),
        "message": "Exercise updated successfully",
        "status": "ok"
    }

@router.delete("/{id}")
async def delete_exercise(id: int, db: AsyncSession = Depends(get_db)):
    service = ExerciseService(db)
    success = await service.delete_exercise(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with ID {id} not found"
        )
    return {
        "data": {"id": id},
        "message": "Exercise deleted successfully",
        "status": "ok"
    }

@router.post("/{id}/enrich")
async def enrich_exercise(id: int, db: AsyncSession = Depends(get_db)):
    service = EnrichmentService(db)
    try:
        exercise = await service.enrich_exercise(id)
        return {
            "data": ExerciseResponse.model_validate(exercise),
            "message": "Exercise metadata enriched successfully",
            "status": "ok"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI enrichment failed: {str(e)}"
        )

@router.post("/add-from-pool")
async def add_from_pool(schema: AddFromPoolRequest, db: AsyncSession = Depends(get_db)):
    from backend.app.services.pool_service import PoolService
    service = PoolService(db)
    try:
        exercise = await service.add_to_personal(
            pool_id=schema.pool_id,
            tags=schema.tags,
            name_vie=schema.name_vie
        )
        return {
            "data": ExerciseResponse.model_validate(exercise),
            "message": "Exercise added from pool successfully",
            "status": "ok"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
