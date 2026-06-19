# CLAUDE.md — Developer Reference

This guide summarizes common development commands, test execution scripts, and coding style rules for Fitness OS.

## Development & Build Commands

- **Start Services (Docker)**: `docker compose up --build -d`
- **Stop Services**: `docker compose down`
- **View Backend Logs**: `docker compose logs -f backend`
- **View DB Logs**: `docker compose logs -f db`
- **Check Container Status**: `docker compose ps`

## Database Queries

- **Inspect DB Tables**: `docker compose exec db psql -U fitness -d fitness_os -c "\dt"`
- **Query Table Content**: `docker compose exec db psql -U fitness -d fitness_os -c "SELECT * FROM exercise_master;"`

## Running Tests

- **Run Backend Tests**: `docker compose exec backend env PYTHONPATH=. pytest -c backend/pytest.ini`

## Code Style & Architectural Conventions

- **FastAPI / Python**:
  - Always use `async`/`await` for database operations.
  - Enforce explicit type hints for function signatures.
  - Separate routes (routers) from business logic (services).
  - Use Pydantic schemas for request/response serialization.
- **Frontend / JS**:
  - Pure Vanilla JS loaded without build step via standard `<script>` tags.
  - Use Alpine.js stores (`js/stores/`) to manage reactive state.
  - Prefix all network queries through `js/api.js`.
- **CSS**:
  - Standard Vanilla CSS only (dark-mode by default).
  - Global design tokens must reside in `variables.css`.
  - Responsive layouts should be mobile-first.
