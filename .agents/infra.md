# 🐳 Infrastructure Worker — Agent Prompt

> **Role**: DevOps / Infrastructure
> **Scope**: Root config files + Docker setup
> **Trước khi bắt đầu**: Đọc `AGENTS.md` ở root → rồi đọc file này.

---

## 🔄 Handoff (BẮT BUỘC)

### Khi bắt đầu
- Đọc `.handoffs/` nếu có files — để biết context trước đó

### Khi kết thúc
- Viết `.handoffs/infra-done.md` với format trong `AGENTS.md`
- **BẮT BUỘC** liệt kê:
  - Docker services nào đang chạy (ports, healthchecks)
  - Database connection info (user, db name, tables created)
  - Files đã tạo/sửa
  - Hướng dẫn cho backend worker: cách chạy, env vars available

---

## 🎯 Nhiệm vụ

Bạn là infra worker cho dự án Fitness OS. Bạn chịu trách nhiệm:

1. **Docker Compose** — PostgreSQL + Backend services
2. **Environment config** — `.env.example`, `.env`
3. **Dockerfile** — Backend container build
4. **Git setup** — `.gitignore`
5. **README** — Project documentation

---

## 📋 Checklist

- [ ] `docker-compose.yml` — PostgreSQL 16 + Backend + volumes + healthchecks
- [ ] `.env.example` — Template env file (NO secrets)
- [ ] `.gitignore` — Python, Node, Docker, env, IDE files
- [ ] `README.md` — Setup instructions, architecture overview
- [ ] Verify: `docker compose up --build` works end-to-end

---

## 🐳 Docker Compose Spec

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"                    # Expose for local dev
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    restart: unless-stopped
    ports:
      - "${APP_PORT:-8000}:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      N8N_WEBHOOK_URL: ${N8N_WEBHOOK_URL}
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./frontend:/app/frontend       # Mount frontend for dev

volumes:
  postgres_data:
```

### Key Design Decisions
- **Frontend mounted as volume** → changes reflect without rebuild during dev
- **PostgreSQL port exposed** → cho phép direct DB access khi debug
- **Health check** → backend chỉ start khi DB ready
- **`unless-stopped`** → auto-restart on server reboot

---

## 📦 Backend Dockerfile Spec

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy frontend for static serving
COPY frontend/ ./frontend/

# Run
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📄 .env.example

```env
# ===== DATABASE =====
POSTGRES_USER=fitness
POSTGRES_PASSWORD=change_me_please
POSTGRES_DB=fitness_os

# ===== N8N =====
# Self-hosted n8n webhook URL (same tailnet)
N8N_WEBHOOK_URL=http://n8n.local:5678/webhooks/enrich

# ===== APP =====
APP_HOST=0.0.0.0
APP_PORT=8000
```

---

## 📄 .gitignore

```gitignore
# Environment
.env
!.env.example

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.venv/
venv/

# Docker
postgres_data/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
```

---

## 🚫 Boundaries

- **KHÔNG** sửa code trong `backend/app/` — đó là scope của backend worker
- **KHÔNG** sửa files trong `frontend/` — đó là scope của frontend worker
- **KHÔNG** thêm services mới vào Docker Compose mà không được approve
- Focus: config, infra, deployment readiness

---

## 🧪 Verification

```bash
# 1. Build and start
docker compose up --build -d

# 2. Check all services healthy
docker compose ps

# 3. Check PostgreSQL
docker compose exec db psql -U fitness -d fitness_os -c "SELECT 1;"

# 4. Check backend
curl http://localhost:8000/api/exercises

# 5. Check frontend served
curl -I http://localhost:8000/

# 6. Logs
docker compose logs -f backend
```
