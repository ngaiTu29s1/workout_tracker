# 🏋️‍♂️ Fitness OS — Workout Tracker & Planner

Fitness OS is a premium, mobile-first Web App (PWA-ready) designed for tracking and planning workouts. It is vibe-coded with a multi-agent developer system.

---

## 🏗️ Tech Stack

- **Backend**: Python 3.12 + FastAPI + Uvicorn
- **ORM**: SQLAlchemy 2.0 (async) + asyncpg
- **Database**: PostgreSQL 16 (Docker)
- **Frontend**: HTML5 + Vanilla CSS + Alpine.js
- **Libraries**: SortableJS (Drag & Drop), Chart.js (Charts)
- **Infra**: Docker Compose

---

## 📂 Project Structure

```
workout_checker/
├── docs/                        # Project documentation
│   ├── AGENTS.md                # Shared agent context & conventions
│   ├── PLAN.md                  # Implementation plan
│   └── instruct.md              # Original product specification
│
├── data/                        # Local data directory (Gitignored)
│   └── exercise-pool/           # Media pool for exercise instructions
│       ├── exercises.json       # Exercise master list
│       ├── images/              # Demonstration images
│       └── videos/              # Demonstration videos
│
├── backend/                     # FastAPI Backend service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # Application entry point & static mounts
│       ├── database.py          # SQLAlchemy async session
│       ├── config.py            # Environment configurations
│       ├── models/              # SQLAlchemy Models
│       ├── schemas/             # Pydantic Schemas
│       ├── routers/             # API Router handlers
│       ├── services/            # Business Logic layer
│       └── seed/                # DB Seeding logic
│
├── frontend/                    # Vanilla frontend application
│   ├── index.html               # SPA entry point
│   ├── css/                     # Modulized styling files
│   └── js/                      # Alpine.js application logic
│
├── docker-compose.yml           # Local multi-container orchestrator
├── .env.example                 # Template for environment variables
└── README.md                    # This developer guide
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Docker** and **Docker Compose** installed.
- **Python 3.12** (optional, for local development outside Docker).

### 2. Dataset Installation
Because the exercise pool dataset is large and contains rich media, it is gitignored under the `data/` directory.

To setup the dataset locally:
1. Create the local directory path `data/exercise-pool/` at the root of the project.
2. Place the following files inside `data/exercise-pool/`:
   - `exercises.json` (The master database seed file)
   - `images/` (Folder containing exercise pictures)
   - `videos/` (Folder containing exercise videos)
3. During container startup, the directory `./data/exercise-pool` is mounted directly inside the backend service at `/app/static/pool` and served by FastAPI at the `/pool` path (e.g. `/pool/videos/squat.mp4`).

### 3. Local Environment Configuration
Copy `.env.example` to `.env` and adjust the variables as needed:
```bash
cp .env.example .env
```

### 4. Running the Application
Build and start the services using Docker Compose:
```bash
docker compose up --build
```
This command:
1. Starts the PostgreSQL 16 database container.
2. Runs the health check on the database.
3. Builds the FastAPI backend container and starts it on port `8000`.
4. Initializes the database schema and seeds it with data from `data/exercise-pool/exercises.json` (if the database is fresh or partially seeded).
5. Serves the Alpine.js frontend on port `8000` (mapped via Docker volume for live development reload).

Access the application in your browser at:
**[http://localhost:8000](http://localhost:8000)**

---

## 🛠️ Verification & Development

### Accessing APIs and Documentation
- Interactive API docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Exercise pool media assets: [http://localhost:8000/pool/](http://localhost:8000/pool/)

### Running Tests
To run backend tests inside the running container:
```bash
docker compose exec backend pytest tests/ -v
```
