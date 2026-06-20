# 📁 Phase 1: Project Restructure — Worker Instructions

> **Role**: Infra / DevOps
> **Scope**: Folder reorganization, Docker config, static serving
> **Trước khi bắt đầu**: Đọc `AGENTS.md` ở root → đọc `.handoffs/` → đọc file này.

---

## 🎯 Mục tiêu

Tổ chức lại project folder cho chuẩn web app, chuẩn bị cho kiến trúc Pool/Personal.

---

## 📋 Tasks

### 1. Di chuyển docs ra khỏi root

```bash
mkdir -p docs
git mv AGENTS.md docs/AGENTS.md
git mv PLAN.md docs/PLAN.md
git mv instruct.md docs/instruct.md
```

> **LƯU Ý**: Sau khi move, cập nhật tất cả references đến các file này trong:
> - `.agents/*.md` (nếu reference `AGENTS.md` ở root)
> - `README.md`
> - Bất kỳ file nào khác

### 2. Restructure dataset folder

Dataset hiện tại: `exercises-dataset/` (clone repo bên ngoài)

```bash
mkdir -p data/exercise-pool
# Copy chỉ cần thiết (KHÔNG dùng git mv vì đây là clone repo)
cp exercises-dataset/data/exercises.json data/exercise-pool/exercises.json
cp -r exercises-dataset/images/ data/exercise-pool/images/
cp -r exercises-dataset/videos/ data/exercise-pool/videos/
# Sau khi verify, xoá folder cũ
rm -rf exercises-dataset/
```

Cấu trúc mới:
```
data/
└── exercise-pool/
    ├── exercises.json       # 1324 exercises metadata (~5MB)
    ├── images/              # JPG thumbnails (~12MB)
    └── videos/              # GIF demos (~126MB)
```

### 3. Update `.gitignore`

```gitignore
# Exercise pool data (local only, not tracked)
data/

# Remove old entry
# exercises-dataset/   ← XÓA DÒNG NÀY
```

> **QUAN TRỌNG**: Toàn bộ `data/` được gitignore. Không track bất kỳ file nào trong data/.

### 4. Update `docker-compose.yml`

```yaml
services:
  backend:
    # ... existing config ...
    volumes:
      - ./backend:/app/backend
      - ./frontend:/app/frontend
      - ./data/exercise-pool:/app/static/pool    # ← THÊM mount pool data
    environment:
      # ... existing vars ...
      POOL_DATA_PATH: /app/static/pool           # ← THÊM env var
```

Bỏ dòng `version: '3.8'` (obsolete warning).

### 5. Update `backend/app/main.py` — Serve pool media

Thêm static file serving cho pool images/videos:

```python
from fastapi.staticfiles import StaticFiles
import os

# Mount pool static files (images, videos)
pool_path = os.getenv("POOL_DATA_PATH", "/app/static/pool")
if os.path.exists(pool_path):
    app.mount("/pool", StaticFiles(directory=pool_path), name="pool")
```

Kết quả: 
- `GET /pool/images/0001-2gPfomN.jpg` → trả ảnh
- `GET /pool/videos/0001-2gPfomN.gif` → trả GIF demo

### 6. Update `README.md`

Viết README mô tả:
- Project overview
- Cách setup (docker compose up)
- Cách download dataset (vì gitignored)
- Link đến docs/

---

## ⚠️ Lưu ý quan trọng

1. **KHÔNG sửa bất kỳ logic BE/FE nào** — chỉ restructure folder + config
2. **Verify sau khi restructure**: `docker compose down -v && docker compose up --build` phải chạy được
3. **Dataset JSON schema** (để backend worker biết):
   ```json
   {
     "id": "0001",
     "name": "3/4 sit-up",
     "category": "waist",
     "body_part": "waist", 
     "equipment": "body weight",
     "instructions": { "en": "...", "it": "...", "tr": "..." },
     "instruction_steps": { "en": ["Step 1...", "Step 2..."] },
     "muscle_group": "hip flexors",
     "secondary_muscles": ["hip flexors", "lower back"],
     "target": "abs",
     "image": "images/0001-2gPfomN.jpg",
     "gif_url": "videos/0001-2gPfomN.gif",
     "created_at": "2026-03-18T12:31:32.854798+00:00"
   }
   ```
4. **Total exercises**: 1324

---

## 🔄 Handoff

Khi hoàn thành, viết `.handoffs/phase1-done.md` với:
- Cấu trúc folder mới (tree)
- Docker compose changes
- Static serving URLs
- Hướng dẫn cho Phase 2 backend worker
