FROM node:22-alpine AS web
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app PATH=/app/.venv/bin:$PATH
WORKDIR /app
RUN pip install --no-cache-dir uv==0.8.13
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY server/ server/
COPY worker/ worker/
COPY --from=web /build/web/dist web/dist
EXPOSE 8095
CMD ["rw", "serve", "--host", "0.0.0.0", "--port", "8095"]

FROM docker:29-cli AS docker_cli
FROM runtime AS runner
COPY --from=docker_cli /usr/local/bin/docker /usr/local/bin/docker
EXPOSE 8096
CMD ["uvicorn", "server.runner_controller:app", "--host", "0.0.0.0", "--port", "8096"]
