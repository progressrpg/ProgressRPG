# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7



# --------------------------
# Base stage: Python + dependencies
# --------------------------
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS base

# Prevents .pyc files and unbuffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/entrypoint.sh"]
WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.

# Install system dependencies
RUN apt-get update && apt-get install -y \
        python3-dev \
        libpq-dev \
        build-essential \
        gdal-bin \
        libgdal-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Switch to the non-privileged user to run the application.
# USER appuser

# Copy the source code into the container.
COPY . .

# Copy entrypoint first (with executable permissions)
COPY --chmod=755 entrypoint.sh /app/entrypoint.sh
# --------------------------
# Web stage: builds React
# --------------------------
FROM base AS web

USER root

# Install Node (for building React)
WORKDIR /app/frontend
RUN apt-get update \
    && apt-get install -y nodejs npm \
    && npm install
RUN VITE_API_BASE_URL=$VITE_API_BASE_URL npm run build:production

WORKDIR /app

RUN mkdir -p /app/staticfiles \
    && chown -R appuser:appuser /app/staticfiles
RUN python manage.py collectstatic --noinput

USER appuser

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
#CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "progress_rpg.asgi:application"]

# --------------------------
# Celery stage: Python only
# --------------------------
FROM base AS celery
# No npm, no frontend build
CMD ["celery", "-A", "progress_rpg", "worker", "--loglevel=info"]

# --------------------------
# Celery-beat stage: Python only
# --------------------------
FROM base AS celery-beat
CMD ["celery", "-A", "progress_rpg", "beat", "--loglevel=info", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"]
