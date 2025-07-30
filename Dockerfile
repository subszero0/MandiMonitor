# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# ---------- builder ----------
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir poetry
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root
COPY . .
RUN poetry install --only-root

# ---------- runtime ----------
FROM base AS runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python*/site-packages /usr/local/lib/python*/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app .
EXPOSE 8000
CMD ["python", "-m", "bot.main"] 