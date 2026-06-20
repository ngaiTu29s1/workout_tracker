# 🔧 Phase 2: Backend — Exercise Pool + Personal Architecture

> **Role**: Backend Developer
> **Scope**: DB models, API endpoints, seed logic, pool service
> **Trước khi bắt đầu**: Đọc `docs/AGENTS.md` → `.handoffs/phase1-done.md` → đọc file này.

---

## 🎯 Mục tiêu

Implement kiến trúc 2 tầng: **Exercise Pool** (1324 bài, read-only reference) + **Personal Exercises** (user chọn tập).

---

## 🏗️ Kiến trúc tổng quan

```
exercise_pool (1324 rows)          exercise_master (personal)
┌─────────────────────────┐        ┌──────────────────────────────┐
│ id (PK)                 │◄───────│ pool_id (FK, nullable)       │
│ pool_id ("0001")        │        │ id (PK)                      │
│ name                    │        │ name_eng                     │
│ category, body_part     │        │ name_vie                     │
│ equipment               │        │ instructions (override/pool) │
│ instructions_en         │        │ video_url (override/pool)    │
│ instructions_vi          │        │ image_url (override/pool)    │
│ muscle_group            │        │ pro_tips                     │
│ secondary_muscles       │        │ tracking_type                │
│ image_path, gif_path    │        │ primary_muscle               │
│ target                  │        │ secondary_muscle, tags       │
└─────────────────────────┘        └──────────────────────────────┘
```

---

## 📋 Tasks

### 1. New Model: `exercise_pool`

**File**: `backend/app/models/pool.py`

```python
class ExercisePool(Base):
    __tablename__ = "exercise_pool"
    
    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(String(10), unique=True, nullable=False, index=True)  # "0001", "0002"
    name = Column(String(255), nullable=False, index=True)                  # English name
    category = Column(String(100))           # "chest", "back", "waist"
    body_part = Column(String(100))          # same/similar to category
    equipment = Column(String(100))          # "barbell", "body weight", "machine"
    target = Column(String(100))             # target muscle ("abs", "pectorals")
    instructions_en = Column(Text)           # English instructions (full text)
    instructions_vi = Column(Text)           # Vietnamese (batch translated, nullable)
    muscle_group = Column(String(100))       # primary muscle
    secondary_muscles = Column(JSONB, default=[])
    image_path = Column(String(255))         # "images/0001-xxx.jpg"
    gif_path = Column(String(255))           # "videos/0001-xxx.gif"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 2. Modify Model: `exercise_master`

**File**: `backend/app/models/exercise.py`

Thêm foreign key link đến pool:

```python
pool_id = Column(Integer, ForeignKey("exercise_pool.id"), nullable=True)
pool = relationship("ExercisePool", backref="personal_exercises")
```

> **LƯU Ý**: `pool_id = None` nghĩa là bài tập tạo thủ công (không có trong pool).

### 3. New Schemas: Pool

**File**: `backend/app/schemas/pool.py`

```python
class PoolSearchResult(BaseModel):
    id: int
    pool_id: str
    name: str
    category: str | None
    equipment: str | None
    target: str | None
    muscle_group: str | None
    image_path: str | None
    gif_path: str | None

class PoolDetail(PoolSearchResult):
    instructions_en: str | None
    instructions_vi: str | None
    secondary_muscles: list[str]
    body_part: str | None

class AddFromPoolRequest(BaseModel):
    pool_id: int           # exercise_pool.id
    tags: list[str] = []   # user-assigned tags (push, pull, legs, etc.)
    name_vie: str | None = None  # optional VN name override
```

### 4. New Service: Pool

**File**: `backend/app/services/pool_service.py`

```python
class PoolService:
    async def search(self, query: str, limit: int = 20) -> list[ExercisePool]:
        """Fuzzy search pool by name. Use ILIKE for simplicity."""
        # WHERE name ILIKE '%bench%press%'
        # Tách query thành words, join bằng %
        # VD: "bench press" → "%bench%press%"
    
    async def get_by_id(self, pool_id: int) -> ExercisePool:
        """Get single pool exercise by DB id."""
    
    async def get_categories(self) -> dict:
        """Return distinct body_parts and equipment types."""
    
    async def add_to_personal(self, pool_id: int, tags: list[str], name_vie: str = None) -> ExerciseMaster:
        """Copy pool exercise → personal exercise_master."""
        # 1. Fetch pool exercise
        # 2. Create ExerciseMaster with:
        #    - name_eng = pool.name
        #    - name_vie = name_vie or None (n8n dịch sau)
        #    - instructions = pool.instructions_vi or pool.instructions_en
        #    - image_url = f"/pool/{pool.image_path}" (served by static mount)
        #    - video_url = f"/pool/{pool.gif_path}"
        #    - primary_muscle = pool.muscle_group
        #    - secondary_muscle = pool.secondary_muscles
        #    - tags = tags (user-provided)
        #    - tracking_type = infer from equipment/category
        #    - pool_id = pool.id (link back)
        # 3. Return created exercise
```

### 5. New Router: Pool

**File**: `backend/app/routers/pool.py`

```
GET  /api/pool/search?q=bench+press&limit=20
     → PoolService.search() → list[PoolSearchResult]

GET  /api/pool/{id}
     → PoolService.get_by_id() → PoolDetail

GET  /api/pool/categories
     → PoolService.get_categories() → { body_parts: [...], equipment: [...] }

POST /api/exercises/add-from-pool
     → PoolService.add_to_personal() → ExerciseResponse
```

> **LƯU Ý**: `POST add-from-pool` nên nằm trong `routers/exercises.py` vì nó tạo personal exercise.

### 6. Seed Logic — Rewrite

**File**: `backend/app/seed/seed_data.py`

```python
import json

async def seed_pool(db: AsyncSession):
    """Seed exercise_pool từ exercises.json (1324 rows)."""
    pool_count = await db.scalar(select(func.count(ExercisePool.id)))
    
    if pool_count >= 1324:
        logger.info(f"Pool already seeded ({pool_count}). Skipping.")
        return
    
    # Clear and reseed if partial
    if pool_count > 0:
        await db.execute(ExercisePool.__table__.delete())
        await db.flush()
    
    # Load JSON
    json_path = os.getenv("POOL_DATA_PATH", "/app/static/pool") + "/exercises.json"
    with open(json_path) as f:
        exercises = json.load(f)
    
    for ex in exercises:
        pool_ex = ExercisePool(
            pool_id=ex["id"],
            name=ex["name"],
            category=ex.get("category"),
            body_part=ex.get("body_part"),
            equipment=ex.get("equipment"),
            target=ex.get("target"),
            instructions_en=ex.get("instructions", {}).get("en"),
            muscle_group=ex.get("muscle_group"),
            secondary_muscles=ex.get("secondary_muscles", []),
            image_path=ex.get("image"),       # "images/0001-xxx.jpg"
            gif_path=ex.get("gif_url"),       # "videos/0001-xxx.gif"
        )
        db.add(pool_ex)
    
    await db.commit()
    logger.info(f"Seeded {len(exercises)} exercises into pool.")

async def seed_personal_defaults(db: AsyncSession):
    """Seed 33 bài tập mặc định cho user (link to pool)."""
    personal_count = await db.scalar(select(func.count(ExerciseMaster.id)))
    if personal_count > 0:
        logger.info(f"Personal exercises exist ({personal_count}). Skipping.")
        return
    
    # Mapping: name keyword → pool name → tags
    DEFAULT_EXERCISES = [
        {"search": "barbell bench press",  "tags": ["push", "upper_body", "compound"]},
        {"search": "barbell deadlift",     "tags": ["pull", "legs", "compound"]},
        {"search": "barbell curl",         "tags": ["pull", "upper_body", "isolation"]},
        # ... 33 entries, mỗi entry search pool bằng name
    ]
    
    for entry in DEFAULT_EXERCISES:
        # Fuzzy match pool
        pool_ex = await db.scalar(
            select(ExercisePool).where(
                ExercisePool.name.ilike(f"%{entry['search']}%")
            ).limit(1)
        )
        if pool_ex:
            personal = ExerciseMaster(
                pool_id=pool_ex.id,
                name_eng=pool_ex.name.title(),
                instructions=pool_ex.instructions_en,
                image_url=f"/pool/{pool_ex.image_path}" if pool_ex.image_path else None,
                video_url=f"/pool/{pool_ex.gif_path}" if pool_ex.gif_path else None,
                primary_muscle=pool_ex.muscle_group,
                secondary_muscle=pool_ex.secondary_muscles,
                tags=entry["tags"],
            )
            db.add(personal)
    
    await db.commit()

async def seed_db(db: AsyncSession):
    """Main seed entry point."""
    await seed_pool(db)
    await seed_personal_defaults(db)
    await seed_weekly_presets(db)  # existing preset seed
```

### 7. Vietnamese Batch Translation

Cho phiên bản đầu tiên, `instructions_vi` trong pool để `NULL`.

Thêm endpoint để trigger batch translate (gọi n8n cho từng batch):

```
POST /api/pool/batch-translate?limit=50
→ Lấy 50 exercises chưa có instructions_vi
→ Gọi n8n webhook dịch từng cái
→ Update instructions_vi trong pool
```

Hoặc có thể để Phase sau. **Ưu tiên** là pool + personal architecture chạy trước.

### 8. Modify Existing Exercise Schemas/Responses

Khi trả `ExerciseResponse`, include pool info nếu có:

```python
class ExerciseResponse(BaseModel):
    # ... existing fields ...
    pool_id: int | None = None
    pool_image: str | None = None  # computed from pool
    pool_gif: str | None = None    # computed from pool
```

---

## ⚠️ Lưu ý quan trọng

1. **Alembic/Migration**: Nếu project chưa dùng Alembic, tạo bảng mới qua `Base.metadata.create_all`. Nếu đã có data, cần handle migration cẩn thận.
2. **Pool data path**: Đọc từ env var `POOL_DATA_PATH` (default `/app/static/pool`). Phase 1 đã mount volume.
3. **Image/GIF URLs**: Frontend sẽ gọi `/pool/images/xxx.jpg` — đã được serve static bởi FastAPI mount.
4. **Backward compatibility**: Existing endpoints (`/api/exercises`, `/api/workouts`, etc.) PHẢI giữ nguyên behavior.
5. **Tracking type inference**: Từ equipment/category:
   - `body weight` → `BODYWEIGHT_REPS`
   - `cardio machine` / `stationary bike` → `TIME`
   - Còn lại → `WEIGHT_REPS`

---

## 🧪 Tests

```python
# test_pool.py
async def test_pool_search():
    """Search 'bench' trả ≥1 result"""

async def test_pool_detail():
    """Get pool exercise by id"""

async def test_add_from_pool():
    """Add pool exercise → creates personal exercise with correct fields"""

async def test_personal_still_works():
    """Existing CRUD endpoints vẫn hoạt động"""
```

---

## 🔄 Handoff

Viết `.handoffs/phase2-done.md` với:
- DB schema mới (2 tables)
- API endpoints mới + examples curl
- Seed results (pool count, personal count)
- Image/GIF URL format cho frontend
- Hướng dẫn cho Phase 3 frontend worker
