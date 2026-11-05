# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.13.1 AS uv
FROM python:3.13-slim-bookworm AS build
WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm AS runtime
WORKDIR /app
RUN groupadd --gid 1001 app && useradd --uid 1001 --gid app --create-home app
COPY --from=build --chown=1001:1001 /app/.venv /app/.venv
COPY --chown=1001:1001 backend/app ./app
COPY --chown=1001:1001 backend/alembic ./alembic
COPY --chown=1001:1001 backend/alembic.ini ./
COPY --from=frontend --chown=1001:1001 /frontend/dist /app/static
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 1001:1001
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
