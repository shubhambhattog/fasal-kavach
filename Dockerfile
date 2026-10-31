# Stage 1: build the React frontend
FROM node:24-slim AS web
WORKDIR /web
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# Stage 2: Python API that also serves the built frontend
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN useradd -m -u 1000 app
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ ./
COPY --from=web /web/dist /app/frontend/dist
RUN mkdir -p /app/data/cache && chown -R app /app
USER app
ENV PATH="/app/backend/.venv/bin:$PATH" PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
