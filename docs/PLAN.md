# Fitness OS — Implementation Plan

## Tổng quan quyết định

| Hạng mục | Quyết định |
|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy (async) + asyncpg |
| Database | PostgreSQL 16 (Docker) |
| Frontend | HTML5 + **Vanilla CSS** + Alpine.js + SortableJS + Chart.js |
| CSS Strategy | Vanilla CSS (dark mode, glassmorphism, micro-animations) — không dùng Tailwind |
| n8n | Self-hosted cùng tailnet, gọi qua env var `N8N_WEBHOOK_URL` |
| Auth | Không có auth — single user, tailnet only |
| Deployment | Docker Compose (PostgreSQL + Backend), serve frontend từ FastAPI |
| PWA | Chưa làm, tính sau |

> [!IMPORTANT]
> **CSS Choice**: Document gốc ghi Tailwind CSS, nhưng tôi chọn **Vanilla CSS** để có toàn quyền kiểm soát design premium (glassmorphism, custom animations, dark theme chi tiết). Kết quả cuối cùng sẽ đẹp hơn và không phụ thuộc build tool. Nếu bạn muốn Tailwind, cho tôi biết.

---

## User Review Required

### Seed Data
Tôi sẽ tạo sẵn **~30 bài tập phổ biến** (Bench Press, Squat, Deadlift, Pull-up, etc.) với đầy đủ metadata. Bạn có danh sách bài tập cụ thể muốn import không, hay để tôi chọn bộ phổ biến nhất?

### n8n LLM Prompt
Tôi sẽ tạo backend endpoint `POST /api/exercises/{id}/enrich` gọi tới n8n webhook. n8n flow sẽ cần bạn setup riêng (nằm ngoài scope code này). Backend chỉ:
1. Gửi `{exercise_id, name_eng}` → n8n webhook
2. n8n trả về JSON enriched data
3. Backend update vào DB

→ **Confirm đúng flow này?**

---

## Proposed Changes

### Project Structure

```
fitness-os/
├── docker-compose.yml
├── .env.example
├── .env
├── .gitignore
├── docs/instruct.md
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings from env
│   │   ├── database.py          # SQLAlchemy async engine + session
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── exercise.py      # exercise_master
│   │   │   ├── preset.py        # weekly_presets
│   │   │   ├── workout_log.py   # daily_workout_log
│   │   │   └── stats.py         # workout_aggregated_stats
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── exercise.py      # Pydantic models
│   │   │   ├── preset.py
│   │   │   ├── workout.py
│   │   │   └── stats.py
│   │   │
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── exercises.py     # CRUD + AI enrich trigger
│   │   │   ├── presets.py       # Weekly preset management
│   │   │   ├── workouts.py      # Log management + session
│   │   │   ├── calendar.py      # Smart calendar engine
│   │   │   └── stats.py         # Statistics & chart data
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── exercise_service.py
│   │   │   ├── workout_service.py
│   │   │   ├── calendar_service.py  # Merge presets + overrides + logs
│   │   │   ├── stats_service.py     # Metrics calculation engine
│   │   │   └── enrichment_service.py # n8n webhook caller
│   │   │
│   │   └── seed/
│   │       ├── __init__.py
│   │       └── seed_data.py     # ~30 exercises + weekly presets
│   │
│   └── tests/
│       └── ...
│
└── frontend/
    ├── index.html               # SPA shell
    ├── manifest.json            # PWA manifest (basic)
    │
    ├── css/
    │   ├── variables.css        # Design tokens (colors, spacing, fonts)
    │   ├── base.css             # Reset + typography + dark theme
    │   ├── components.css       # Cards, buttons, inputs, modals
    │   ├── layout.css           # Grid, responsive breakpoints
    │   ├── animations.css       # Micro-animations, transitions
    │   └── views.css            # View-specific styles
    │
    ├── js/
    │   ├── app.js               # Alpine.js app init + routing
    │   ├── api.js               # Fetch wrapper for backend
    │   ├── stores/
    │   │   ├── exercise-store.js
    │   │   ├── workout-store.js
    │   │   ├── calendar-store.js
    │   │   └── stats-store.js
    │   │
    │   ├── components/
    │   │   ├── exercise-card.js
    │   │   ├── workout-input.js
    │   │   ├── calendar-grid.js
    │   │   └── chart-widget.js
    │   │
    │   └── utils/
    │       ├── date-utils.js
    │       └── format-utils.js
    │
    └── assets/
        ├── icons/
        └── images/
```

---

### Component 1: Docker & Infrastructure

#### [NEW] docker-compose.yml
- PostgreSQL 16 service với volume persist
- Backend service (FastAPI) build từ `backend/Dockerfile`
- Shared network
- Health checks cho PostgreSQL
- Environment variables từ `.env`

#### [NEW] .env.example
```env
# Database
POSTGRES_USER=fitness
POSTGRES_PASSWORD=<change-me>
POSTGRES_DB=fitness_os
DATABASE_URL=postgresql+asyncpg://fitness:<password>@db:5432/fitness_os

# n8n
N8N_WEBHOOK_URL=http://<n8n-host>/webhooks/enrich

# App
APP_HOST=0.0.0.0
APP_PORT=8000
```

#### [NEW] backend/Dockerfile
- Python 3.12 slim image
- Install requirements
- Uvicorn as ASGI server
- Serve cả frontend static files

---

### Component 2: Database & Models

#### [NEW] backend/app/models/*.py
- SQLAlchemy 2.0 async models mapping 5 bảng (4 bảng gốc trong docs/instruct.md + 1 bảng `daily_overrides` để lưu lịch tập ghi đè từng ngày mà không làm thay đổi preset hàng tuần)
- Relationships giữa các bảng
- Index trên `workout_date`, `exercise_id`

#### [NEW] backend/app/database.py
- AsyncEngine + AsyncSession factory
- Connection pool config
- Init function tạo tables

#### [NEW] Alembic migrations
- Initial migration tạo 5 bảng
- Seed data migration

---

### Component 3: Backend API

#### [NEW] backend/app/routers/exercises.py
| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/exercises` | List all (with search, filter by tag/muscle) |
| GET | `/api/exercises/{id}` | Get one |
| POST | `/api/exercises` | Create |
| PUT | `/api/exercises/{id}` | Update |
| DELETE | `/api/exercises/{id}` | Delete |
| POST | `/api/exercises/{id}/enrich` | Trigger AI enrichment via n8n |

#### [NEW] backend/app/routers/presets.py
| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/presets` | Get all 7 days |
| PUT | `/api/presets/{day}` | Set routine_tag for a day |
| PUT | `/api/presets` | Bulk update all 7 days |

#### [NEW] backend/app/routers/workouts.py
| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/workouts?date=YYYY-MM-DD` | Get workout log for a date |
| POST | `/api/workouts` | Log a workout set |
| PUT | `/api/workouts/{id}` | Update tracking_data |
| DELETE | `/api/workouts/{id}` | Delete log entry |
| POST | `/api/workouts/{id}/complete` | Mark exercise completed |

#### [NEW] backend/app/routers/calendar.py
| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/calendar?start=&end=` | Smart calendar (presets + overrides + logs merged) |
| POST | `/api/calendar/override` | Override a specific date's routine |

#### [NEW] backend/app/routers/stats.py
| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/stats/exercise/{id}?range=30d` | Stats for one exercise |
| GET | `/api/stats/overview?range=30d` | Overall dashboard stats |

#### [NEW] backend/app/services/stats_service.py
- **Volume** = Σ(weight × reps) per exercise per day
- **Max Weight** = MAX(weight) per exercise per day
- **Total Reps** = Σ(reps) per exercise per day
- **Total Time** = Σ(seconds) per exercise per day (for TIME type)
- Auto UPSERT vào `workout_aggregated_stats` khi log workout

#### [NEW] backend/app/services/enrichment_service.py
- HTTP client gọi `N8N_WEBHOOK_URL` với `{exercise_id, name_eng}`
- Nhận JSON response từ n8n
- Update `exercise_master` record
- Error handling + timeout

---

### Component 4: Frontend

#### [NEW] frontend/css/variables.css — Design Tokens
```css
:root {
  /* Dark theme palette */
  --bg-primary: #0a0a0f;
  --bg-secondary: #12121a;
  --bg-card: rgba(255, 255, 255, 0.04);
  --bg-glass: rgba(255, 255, 255, 0.06);
  
  /* Accent — vibrant teal/cyan */
  --accent-primary: #00d4aa;
  --accent-secondary: #7c3aed;
  --accent-gradient: linear-gradient(135deg, #00d4aa, #7c3aed);
  
  /* Text */
  --text-primary: #f0f0f5;
  --text-secondary: #8888a0;
  
  /* Typography — Inter from Google Fonts */
  --font-family: 'Inter', system-ui, sans-serif;
  
  /* Spacing, radius, shadows... */
}
```

#### [NEW] frontend/index.html
- SPA shell với Alpine.js routing (hash-based)
- 5 views: Catalog, Calendar, Session, Stats, Settings
- Bottom navigation bar (mobile) / Sidebar (desktop)
- CDN imports: Alpine.js, SortableJS, Chart.js, Inter font

#### [NEW] frontend/js/app.js — Alpine.js App
- Hash-based router: `#catalog`, `#calendar`, `#session`, `#stats`
- Global stores: exercises, workouts, calendar, stats
- Reactive data binding

#### Design Highlights
- **Glassmorphism cards** với backdrop-filter blur
- **Micro-animations**: button press scale, card hover lift, slide-in transitions
- **Gym-optimized**: Nút 48px+ touch target, high contrast text
- **Responsive**: Mobile grid 1 col → Desktop 3-4 cols
- **Chart.js**: Gradient area charts cho volume/weight trends

---

### Component 5: Seed Data

#### [NEW] backend/app/seed/seed_data.py
~30 bài tập phổ biến, pre-filled metadata:

**Push**: Bench Press, Incline DB Press, OHP, Dips, Tricep Pushdown, Cable Fly
**Pull**: Deadlift, Barbell Row, Pull-up, Lat Pulldown, Face Pull, Bicep Curl
**Legs**: Squat, Leg Press, Leg Extension, Leg Curl, Calf Raise, Romanian DL
**Core**: Plank, Cable Crunch, Hanging Leg Raise
**Cardio**: Treadmill, Rowing Machine

Weekly Presets default:
| Day | Routine |
|---|---|
| Mon | push |
| Tue | pull |
| Wed | leg |
| Thu | push |
| Fri | pull |
| Sat | leg |
| Sun | rest |

---

## Open Questions

> [!IMPORTANT]
> 1. **Seed data list**: Bộ ~30 bài tập ở trên có phù hợp không? Muốn thêm/bớt gì?
> 2. **n8n flow**: Tôi chỉ tạo backend gọi webhook. Bạn tự setup n8n flow riêng, đúng không?
> 3. **Calendar override logic**: Khi override 1 ngày cụ thể (VD: đổi Wednesday từ "leg" sang "push"), thì override đó chỉ áp dụng cho ngày đó hay permanent? Tôi đề xuất: **chỉ ngày đó**, preset vẫn giữ nguyên cho tuần sau.

---

## Verification Plan

### Automated Tests
```bash
# Backend unit tests
docker compose exec backend pytest tests/ -v

# API integration tests
docker compose exec backend pytest tests/integration/ -v
```

### Manual Verification
1. `docker compose up --build` → tất cả services healthy
2. Truy cập `http://localhost:8000` → thấy UI dark mode
3. Exercise Catalog: CRUD hoạt động, search/filter
4. Calendar: hiển thị đúng preset, drag-and-drop override
5. Workout Session: nhập Set/Kg/Rep → log saved → stats updated
6. Stats: Chart.js hiển thị trends
7. AI Enrich: click "Fill AI" → gọi n8n webhook (test với mock nếu n8n chưa ready)

---

## Phased Approach

| Phase | Nội dung | Ưu tiên |
|---|---|---|
| **Phase 1** | Docker + DB + Backend CRUD + Seed Data | 🔴 Critical |
| **Phase 2** | Frontend Shell + Exercise Catalog View | 🔴 Critical |
| **Phase 3** | Calendar View + Drag-and-Drop | 🟡 High |
| **Phase 4** | Workout Session View | 🟡 High |
| **Phase 5** | Stats Dashboard + Chart.js | 🟢 Medium |
| **Phase 6** | AI Enrichment integration | 🟢 Medium |
| **Phase 7** | Polish, animations, mobile optimization | 🔵 Nice-to-have |
