from fastapi import Header, HTTPException, status
from backend.app.config import settings

async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """
    Dependency to verify the X-API-Key header.
    Raises 401 Unauthorized if the key is missing or invalid.
    """
    if not x_api_key or x_api_key != settings.FITNESS_OS_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
