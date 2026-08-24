FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS builder

ENV PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY pyproject.toml README.md requirements.lock ./
COPY src ./src
RUN pip install --require-hashes -r requirements.lock \
    && pip wheel --no-deps --no-build-isolation --wheel-dir /wheels .

FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md alembic.ini requirements-runtime.lock ./
COPY migrations ./migrations
COPY config ./config
COPY data ./data
COPY scripts ./scripts
COPY --from=builder /wheels /wheels
RUN pip install --require-hashes -r requirements-runtime.lock \
    && pip install --no-deps /wheels/*.whl \
    && rm -rf /wheels

RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn europe_visa_jobs.api.app:app --host 0.0.0.0 --port 8000"]
