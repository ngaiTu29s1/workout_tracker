# 🤖 Goal Prompt & Instructions for the Next Worker

> This document is designed to be fed directly into your next AI Coding assistant to resume work seamlessly.

---

## 🎯 System context & Tech Stack

You are working on **Fitness OS**, a mobile-first premium workout planner and tracker application.

### Tech Stack:
- **Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.0 (Async) + Uvicorn
- **Database**: PostgreSQL 16 (Volume persistence on host)
- **Migrations**: Alembic async migrations
- **Frontend**: Vanilla HTML5, Vanilla CSS (Frosted-glass design, no Tailwind), Alpine.js stores
- **Deploy**: Docker compose, automated through a GitHub Actions workflow pinging a self-hosted n8n webhook.

---

## 🚀 Current Project Status

- **CI/CD**: Fixed. Deploy runs `git fetch --all && git reset --hard origin/main` to prevent divergent branch errors. Webhook failure response uses `JSON.stringify()` to escape errors safely.
- **Port Exposure**: Ports `8000:8000` are exposed in both dev and prod compose configurations.
- **Favicon**: Serves a clean, 32x32 PNG file on `/favicon.ico` and `/favicon.png`.
- **Authentication**: The API Key auth middleware and headers have been completely removed. The app runs fully open inside your private Tailnet.

---

## 🛠️ Next Development Goals (Your Task)

When you begin, prioritize implementing the following features:

### Goal 1: Auto-fill GIF & Image for Custom/External Exercises
- **Context**: Currently, exercises added from the pre-seeded pool of 1,324 items automatically load `/pool/images/...` and `/pool/videos/...` local assets. However, custom/external exercises (added manually by the user) have no images or GIFs.
- **Tasks**:
  1. Cấu hình n8n flow để khi nhận tên bài tập ngoài (`name_eng`), thực hiện gọi một Search Engine API (như Tavily/Google) để tìm link ảnh và GIF động tương ứng.
  2. Trả về các trường `image_url` và `video_url` trong JSON response.
  3. Cập nhật `enrichment_service.py` để ghi các đường dẫn ảnh ngoài này vào trường tương ứng của `ExerciseMaster`.

### Goal 2: PWA Configuration (Offline Mode)
- **Tasks**:
  1. Tạo file `manifest.json` đầy đủ với icon ứng dụng.
  2. Cấu hình một Service Worker cơ bản để cache các tài nguyên tĩnh (`index.html`, `js/`, `css/`) giúp ứng dụng có thể hoạt động ngoại tuyến khi người dùng tập ở phòng gym không có mạng.

### Goal 3: PostgreSQL Automated Backups
- **Tasks**:
  1. Viết script chạy cronjob tự động dump cơ sở dữ liệu `fitness_os` định kỳ mỗi ngày một lần để tránh mất lịch sử tập luyện của người dùng.

---

## 💡 Prompt to copy-paste for the next worker:

```text
You are Antigravity, a professional AI coding assistant.
Your goal is to continue development on the Fitness OS codebase.
Please read 'docs/instruct.md' for the original product specification, and 'docs/goal_prompt.md' to see the current status and next targets.

Start by checking the workspace files, running the existing test suite:
`docker compose exec fitness-backend env PYTHONPATH=. pytest backend/tests/ -v`

Then, begin implementing Goal 1: Auto-fill GIF and Image for external/custom exercises.
```
