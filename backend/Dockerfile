FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy frontend for static serving
COPY frontend/ ./frontend/

CMD alembic -c backend/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
