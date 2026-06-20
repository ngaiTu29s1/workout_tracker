from pydantic import BaseModel
from typing import Optional, List

class PoolSearchResult(BaseModel):
    id: int
    pool_id: str
    name: str
    category: Optional[str] = None
    equipment: Optional[str] = None
    target: Optional[str] = None
    muscle_group: Optional[str] = None
    image_path: Optional[str] = None
    gif_path: Optional[str] = None

    class Config:
        from_attributes = True

class PoolDetail(PoolSearchResult):
    instructions_en: Optional[str] = None
    instructions_vi: Optional[str] = None
    secondary_muscles: List[str] = []
    body_part: Optional[str] = None

    class Config:
        from_attributes = True

class AddFromPoolRequest(BaseModel):
    pool_id: int           # exercise_pool.id
    tags: List[str] = []   # user-assigned tags (push, pull, legs, etc.)
    name_vie: Optional[str] = None  # optional VN name override
