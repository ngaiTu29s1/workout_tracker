from fastapi import APIRouter

from backend.app.config import settings

router = APIRouter(prefix="/api/version", tags=["Version"])


@router.get("")
async def get_version():
    return {
        "data": {
            "version": settings.APP_VERSION,
            "commit": settings.GIT_COMMIT,
            "build_time": settings.BUILD_TIME,
        },
        "message": "Version retrieved successfully",
        "status": "ok",
    }
