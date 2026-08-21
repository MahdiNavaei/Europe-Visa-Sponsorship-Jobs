FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY config ./config
COPY data ./data
COPY scripts ./scripts
RUN pip install --upgrade pip && pip install ".[postgres]"

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn europe_visa_jobs.api.app:app --host 0.0.0.0 --port 8000"]
