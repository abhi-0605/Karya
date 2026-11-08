# ──────────────────────────────────────────────────────────────
# KaryaOS Mock TBO APIs — Dockerfile
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# ── dependencies ──────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── application code ──────────────────────────────────────────
COPY . .

# ── runtime config ────────────────────────────────────────────
# Default failure modes: all off.
# Override at runtime: docker run -e MOCK_IT_FAIL_MODE=503 ...
ENV MOCK_IT_FAIL_MODE=none \
    MOCK_ADMIN_FAIL_MODE=none \
    MOCK_PAYROLL_FAIL_MODE=none \
    LEDGER_FILE=/data/mock_ledger.json

# Persist ledger across restarts when /data is a volume
VOLUME ["/data"]

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
