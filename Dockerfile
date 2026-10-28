# syntax=docker/dockerfile:1

# python 3.13 + uv
FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1
WORKDIR /app

# tailwindcss (only used in build step)
FROM base AS css
ENV TAILWINDCSS_VERSION=v4.3.3
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --only-dev
COPY frontend frontend
COPY diagnostics/templates diagnostics/templates
COPY diagnostics/static/diagnostics/app.js diagnostics/static/diagnostics/app.js
RUN uv run --no-sync tailwindcss -i frontend/app.css -o /app/app.css --minify

# diagnostics app
FROM base AS app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

COPY . .
COPY --from=css /app/app.css diagnostics/static/diagnostics/app.css
RUN ENVIRONMENT=dev python manage.py collectstatic --noinput

# run as 'diagnostics' user unprivileged
RUN useradd --create-home diagnostics \
    && mkdir -p /data/uploads \
    && chown diagnostics /data/uploads
USER diagnostics
ENV UPLOAD_ROOT=/data/uploads

EXPOSE 8000
CMD ["sh", "docker/start.sh"]
