# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE} AS builder

ARG UV_VERSION=0.9.18
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY config ./config

RUN uv sync --locked --no-dev

FROM ${PYTHON_IMAGE} AS runtime

ARG BUILD_VERSION=0.1.0
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="cortex" \
      org.opencontainers.image.description="Cortex API and worker runtime" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CORTEX_LOG_LEVEL=INFO \
    PAYLOAD_STORE_PATH=/var/lib/cortex/payloads

WORKDIR /app

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin cortex \
    && mkdir -p /var/lib/cortex/payloads \
    && chown -R cortex:cortex /var/lib/cortex

COPY --from=builder --chown=cortex:cortex /app /app

USER cortex
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"

FROM runtime AS api
CMD ["uvicorn", "cortex.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS worker
HEALTHCHECK NONE
CMD ["cortex-worker", "--role", "noop"]
