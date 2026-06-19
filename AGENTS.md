# 🤖 FITNESS OS — Agent System Prompt (Shared Context)

> Đây là file context dùng chung cho TẤT CẢ AI agents làm việc trên project này.
> Mỗi worker chat PHẢI đọc file này trước khi bắt đầu làm việc.
> Worker-specific prompts nằm trong `.agents/` directory.

---

## 📌 Project Identity

- **Project**: Fitness OS — Workout Tracker & Planner
- **Type**: Mobile-first Web App (PWA-ready)
- **Style**: Vibe-coded, multi-agent development
- **Repo**: `workout_checker/`

---

## 🏗️ Tech Stack (LOCKED — Không thay đổi trừ khi control plane approve)

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Database | PostgreSQL 16 (Docker) |
| Frontend | HTML5 + Vanilla CSS + Alpine.js |
| Drag & Drop | SortableJS |
| Charts | Chart.js |
| Font | Inter (Google Fonts) |
| Infra | Docker Compose |
| AI Enrichment | n8n webhook (external, self-hosted) |

> [!CAUTION]
> **KHÔNG** tự ý thêm library/framework mới (React, Vue, Tailwind, etc.) mà không được control plane approve.

---

## 📂 Project Structure

```
workout_checker/
├── AGENTS.md                    # ← BẠN ĐANG ĐỌC FILE NÀY
├── PLAN.md                      # Implementation plan chi tiết
├── instruct.md                  # Đặc tả gốc từ product owner
├── docker-compose.yml
├── .env.example
├── .env                         # ⛔ KHÔNG commit
├── .gitignore
├── README.md
│
├── .agents/                     # Worker-specific prompts
│   ├── backend.md               # Backend worker instructions
│   ├── frontend.md              # Frontend worker instructions
│   └── infra.md                 # Infrastructure worker instructions
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              # FastAPI app + static file serving
│   │   ├── config.py            # Pydantic Settings (env-based)
│   │   ├── database.py          # Async engine + session factory
│   │   ├── models/              # SQLAlchemy models (4 tables)
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── routers/             # API route handlers
│   │   ├── services/            # Business logic layer
│   │   └── seed/                # Seed data (~30 exercises)
│   └── tests/
│
└── frontend/
    ├── index.html               # SPA shell (Alpine.js)
    ├── css/
    │   ├── variables.css        # Design tokens
    │   ├── base.css             # Reset + typography
    │   ├── components.css       # Reusable UI components
    │   ├── layout.css           # Grid + responsive
    │   ├── animations.css       # Micro-animations
    │   └── views.css            # View-specific styles
    ├── js/
    │   ├── app.js               # Alpine.js init + hash router
    │   ├── api.js               # Fetch wrapper → backend
    │   ├── stores/              # Alpine.js reactive stores
    │   ├── components/          # JS component logic
    │   └── utils/               # Date/format helpers
    └── assets/
```

---

## 🎨 Design Conventions

### CSS
- **Vanilla CSS only** — no frameworks, no preprocessors
- **Dark mode first** — light mode is NOT planned
- **Design tokens** in `variables.css` — mọi color/spacing/radius dùng CSS custom properties
- **Glassmorphism** — cards dùng `backdrop-filter: blur()` + semi-transparent bg
- **Micro-animations** — hover, press, slide-in, fade. Dùng CSS `transition` và `@keyframes`
- **Mobile-first** — base styles cho mobile, `@media (min-width: ...)` cho desktop

### Color Palette
```css
--bg-primary: #0a0a0f;        /* Main background */
--bg-secondary: #12121a;      /* Cards/sections */
--bg-card: rgba(255,255,255,0.04);
--bg-glass: rgba(255,255,255,0.06);
--accent-primary: #00d4aa;    /* Teal — primary actions */
--accent-secondary: #7c3aed;  /* Purple — secondary/gradient */
--text-primary: #f0f0f5;
--text-secondary: #8888a0;
--danger: #ef4444;
--success: #22c55e;
--warning: #f59e0b;
```

### Touch Targets
- Minimum **48px** height cho tất cả buttons/interactive elements
- Input fields **56px** height
- Padding generous, finger-friendly

---

## 🔌 API Conventions

### Base URL
```
/api/...
```

### Endpoints (đầy đủ trong PLAN.md)
- `/api/exercises` — CRUD + AI enrich
- `/api/presets` — Weekly schedule
- `/api/workouts` — Daily workout logs
- `/api/calendar` — Smart calendar (merge presets + overrides)
- `/api/stats` — Aggregated statistics for charts

### Response Format
```json
{
  "data": { ... },
  "message": "Success",
  "status": "ok"
}
```

### Error Format
```json
{
  "detail": "Error message",
  "status": "error"
}
```

---

## 🗄️ Database Conventions

- **4 tables**: `exercise_master`, `weekly_presets`, `daily_workout_log`, `workout_aggregated_stats`
- Schema chi tiết → xem `instruct.md` Section 2
- **JSONB** cho `tracking_data`, `secondary_muscle`, `tags`
- **CASCADE delete** trên foreign keys
- **UPSERT** cho stats aggregation (unique constraint trên `date + exercise_id + metric_type`)

---

## 🐳 Docker Conventions

- `docker compose up --build` phải chạy được từ root directory
- Backend serve frontend static files tại `/` 
- PostgreSQL data persist qua Docker volume
- Tất cả config qua `.env` file
- Health check cho PostgreSQL trước khi backend start

---

## 📏 Code Style Rules

### Python (Backend)
- **Type hints** bắt buộc cho function params và return
- **Async/await** cho tất cả DB operations
- **Pydantic** cho validation (schemas/)
- **Service layer** — routers KHÔNG chứa business logic, gọi services
- **Docstrings** cho public functions
- Naming: `snake_case` cho functions/variables, `PascalCase` cho classes

### JavaScript (Frontend)
- **ES6+** — `const`/`let`, arrow functions, template literals
- **Alpine.js** `x-data`, `x-bind`, `x-on` patterns
- **No build step** — vanilla JS, loaded via `<script>` tags
- **`api.js`** — tất cả fetch calls đi qua wrapper này
- Naming: `camelCase` cho functions/variables, `PascalCase` cho components

### CSS
- **BEM-like** naming: `.card`, `.card__title`, `.card--active`
- **Custom properties** cho mọi thứ có thể thay đổi
- **Mobile-first** media queries
- Tách file theo concern: tokens, base, components, layout, animations, views

---

## 🔀 Git Conventions

- Branch naming: `feature/<name>`, `fix/<name>`
- Commit messages: English, imperative mood
- `.env` NEVER committed — chỉ `.env.example`

---

## 🚦 Worker Workflow

1. **Đọc `AGENTS.md`** (file này) để hiểu project context
2. **Đọc worker prompt** trong `.agents/<role>.md` để hiểu scope cụ thể
3. **Đọc `PLAN.md`** để hiểu implementation plan
4. **Kiểm tra code hiện tại** trước khi viết — tránh duplicate/conflict
5. **Chỉ làm trong scope** — nếu cần thay đổi ngoài scope, báo lại control plane
6. **Test trước khi báo done** — chạy được, không lỗi syntax/import

---

## 📎 Key References

| File | Mô tả |
|---|---|
| `instruct.md` | Đặc tả product gốc (DB schema, UI views, flows) |
| `PLAN.md` | Implementation plan đã approved |
| `AGENTS.md` | File này — shared agent context |
| `.agents/*.md` | Worker-specific prompts |
