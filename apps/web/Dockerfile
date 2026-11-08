# ──────────────────────────────────────────────────────────────
# KaryaOS Operations Dashboard — Dockerfile (Streamlit)
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install streamlit and pandas
RUN pip install --no-cache-dir \
    streamlit>=1.35 \
    pandas>=2.0 \
    httpx>=0.27 \
    pydantic>=2.7 \
    PyYAML>=6.0 \
    structlog>=24

# Copy entire project for local imports
COPY . /app

ENV PYTHONPATH="/app:/app/backend"
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/_stcore/health')"

CMD ["streamlit", "run", "apps/web/dashboard.py", "--server.port", "3000", "--server.address", "0.0.0.0", "--server.headless", "true"]
