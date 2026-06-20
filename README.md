# 🏋️‍♂️ Fitness OS — Premium Workout Tracker & Planner

A premium, mobile-first Web App designed for seamless workout planning and tracking. Built with high-end aesthetics, full bilingual support, and smart AI enrichment.

---

## ✨ Flex Features

*   **💎 High-End Design**: Built using custom vanilla CSS featuring sleek dark mode, rich gradients, micro-animations, and premium glassmorphic cards.
*   **📅 Interactive Weekly Planner**: Drag-and-drop routines (`Push`, `Pull`, `Legs`, etc.) to schedule your workouts dynamically (powered by SortableJS).
*   **🪄 AI-Powered Enrichment (Auto-fill)**: Integrates with AI agents to automatically translate and enrich exercises with professional instructions, pro-tips, and muscle group tagging.
*   **💾 Local Cache Optimizer**: Auto-caches AI data locally in a JSON file. Automatically restores and seeds custom user exercises (e.g. `One Arm Swing`) instantly even after resetting database containers.
*   **🇻🇳 🇬🇧 Reactively Bilingual**: Instantly toggle the entire interface (names, guidelines, pro-tips, stats) between **Vietnamese** and **English** with zero reload.
*   **📊 Rich Analytical Insights**: Beautiful, interactive charts showing volume progression and workout metrics over time (powered by Chart.js).
*   **⚡ Lightweight Architecture**: Single-container deployment. FastAPI serves the async REST API and hosts the static SPA frontend simultaneously on a single port.

---

## 🛠️ Tech Stack

*   **Backend**: Python 3.12 + FastAPI (Async) + Uvicorn
*   **Database & ORM**: PostgreSQL 16 + SQLAlchemy 2.0 (Async)
*   **Frontend**: Vanilla HTML5 + Alpine.js + Vanilla CSS (No Tailwind)
*   **Libraries**: SortableJS, Chart.js
*   **DevOps**: Docker, Docker Compose

---

## 🚀 Spin it up in 1 Command

Start the entire stack (PostgreSQL + FastAPI + Frontend SPA) in development mode:

```bash
docker compose up --build
```

Access the app at: **[http://localhost:8000](http://localhost:8000)**  
Interactive Swagger API docs: **[http://localhost:8000/docs](http://localhost:8000/docs)**
