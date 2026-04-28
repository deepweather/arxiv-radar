# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python - <<'PY'
import subprocess
import sys
import tomllib

with open("pyproject.toml", "rb") as f:
    dependencies = tomllib.load(f)["project"]["dependencies"]

subprocess.check_call([
    sys.executable,
    "-m",
    "pip",
    "install",
    "--retries",
    "10",
    "--timeout",
    "120",
    *dependencies,
])
PY

COPY app/ ./app/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps .

COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /app/model_cache /app/paper_cache && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
