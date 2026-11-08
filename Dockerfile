# ──────────────────────────────────────────────────────────────
# KaryaOS Backend & Engine — Dockerfile
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install core dependencies
COPY backend/pyproject.toml /app/backend/
RUN pip install --no-cache-dir \
    fastapi>=0.111 \
    uvicorn[standard]>=0.29 \
    "sqlalchemy[asyncio]>=2.0" \
    asyncpg>=0.29 \
    greenlet \
    aiosqlite \
    pydantic>=2.7 \
    pydantic-settings>=2.2 \
    redis[asyncio]>=5.0 \
    "python-jose[cryptography]>=3.3" \
    "passlib[bcrypt]>=1.7" \
    httpx>=0.27 \
    tenacity>=8.3 \
    PyYAML>=6.0 \
    structlog>=24 \
    python-multipart>=0.0.9

# Copy repository
COPY . /app

# Set PYTHONPATH so both /app and /app/backend are importable
ENV PYTHONPATH="/app:/app/backend"
ENV DATABASE_URL="postgresql+asyncpg://karya:karya@postgres:5432/karyaos"
ENV REDIS_URL="redis://redis:6379/0"
ENV MOCK_API_BASE_URL="http://mock-apis:8001"

WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
