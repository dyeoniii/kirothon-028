# syntax=docker/dockerfile:1
# 1) React 빌드 (실제 API 모드)
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
ENV VITE_USE_MOCK=false
RUN npm run build

# 2) FastAPI 실행
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    STATIC_DIR=/app/static STORAGE_DIR=/data/storage DATABASE_URL=sqlite:////data/app.db
RUN apt-get update && apt-get install -y --no-install-recommends fonts-nanum \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=web /web/dist ./static
RUN useradd -m app && mkdir -p /data/storage && chown -R app /data /app
USER app
EXPOSE 10000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
