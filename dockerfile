FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./frontend/dist
WORKDIR /app/backend
RUN pip install --no-cache-dir -e .
ENV CONTEXTPACK_ALLOW_LOCAL=0
ENV CONTEXTPACK_STATIC=/app/frontend/dist
EXPOSE 8000
CMD uvicorn contextpack.api:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000}