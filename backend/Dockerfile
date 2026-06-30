FROM python:3.12-slim

WORKDIR /app

# Build arguments for version info
ARG APP_VERSION
ARG GIT_COMMIT
ARG BUILD_TIME
ENV APP_VERSION=${APP_VERSION:-0.0.0-dev}
ENV GIT_COMMIT=${GIT_COMMIT:-unknown}
ENV BUILD_TIME=${BUILD_TIME:-unknown}

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy VERSION file (fallback for APP_VERSION)
COPY VERSION ./

# Copy backend code
COPY backend/ ./backend/

# Copy frontend for static serving
COPY frontend/ ./frontend/

CMD alembic -c backend/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
