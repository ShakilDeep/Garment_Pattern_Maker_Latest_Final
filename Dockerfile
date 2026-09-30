# Multi-stage image for Render / any container host.
# Serves FastAPI + built React SPA from one process.

FROM node:20-bookworm AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/ ./backend/
COPY fixtures/demo_sources ./fixtures/demo_sources
COPY --from=frontend /src/frontend/dist ./frontend/dist
RUN python -m pip install --no-cache-dir -e "./backend"
ENV DATABASE_URL=sqlite:///garment.db
ENV PYTHONUNBUFFERED=1
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "python -m uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
