# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12

# --------------------------
# Builder stage: compile dependencies
# --------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

# Install build dependencies first (cached separately from app code).
# Cache-mount apt's package/list dirs so a Dockerfile edit that invalidates
# this layer redownloads nothing already fetched by a prior build. The base
# image's docker-clean config would otherwise wipe the cache right after
# install, so it's removed first (see https://docs.docker.com/build/cache/optimize/#use-cache-mounts).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gdal-bin \
        libgdal-dev \
        build-essential \
        gcc

ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so

# Copy ONLY requirements.txt (not app code) so pip install layer caches independently
COPY requirements.txt /tmp/requirements.txt

# Use BuildKit cache mount for pip (persistent across builds)
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --user --no-warn-script-location --no-compile --root-user-action=ignore \
    -r /tmp/requirements.txt


# --------------------------
# Runtime base stage: minimal production runtime
# --------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so
ENV PATH="/usr/local/bin:$PATH"

# Install runtime-only system dependencies BEFORE app code (better cache).
# GeoDjango only needs the GDAL shared library via ctypes (GDAL_LIBRARY_PATH) —
# the versioned libgdalNN runtime package provides that without pulling in
# gdal-bin's CLI toolchain or libgdal-dev's headers. The NN suffix tracks the
# Debian release's GDAL SONAME (e.g. libgdal32 on bookworm, libgdal36 on
# trixie) and shifts whenever the upstream base image does, so resolve it
# dynamically rather than hardcoding it. It also only ships a versioned
# filename (e.g. libgdal.so.32), so symlink the unversioned name
# GDAL_LIBRARY_PATH expects.
# Cache-mounted the same way as the builder stage's apt install above.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update \
    && GDAL_PKG="$(apt-cache search --names-only '^libgdal[0-9]+$' | cut -d' ' -f1)" \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        "$GDAL_PKG" \
    && ln -s "$(find /usr/lib -name 'libgdal.so.*' | sort -V | tail -1)" /usr/lib/libgdal.so

WORKDIR /app

# Create app user BEFORE copying code (avoid invalidating on code changes)
ARG UID=1000
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/bin/bash" \
    --uid "${UID}" \
    appuser \
    && mkdir -p /home/appuser \
    && chown -R appuser:appuser /home/appuser

# Copy pre-built Python packages from builder stage
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
ENV PATH="/home/appuser/.local/bin:$PATH"

# Copy application files (changes frequently, so last in layer chain)
COPY --chown=appuser:appuser . .
COPY --chown=appuser:appuser --chmod=755 entrypoint.sh /app/entrypoint.sh

RUN mkdir -p /app/staticfiles /app/media && chown appuser:appuser /app/staticfiles /app/media

USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]


# --------------------------
# Celery worker service
# --------------------------
FROM runtime-base AS celery

CMD ["celery", "-A", "progress_rpg", "worker", "--loglevel=info"]


# --------------------------
# Celery Beat scheduler service
# --------------------------
FROM runtime-base AS celery-beat

CMD ["celery", "-A", "progress_rpg", "beat", "--loglevel=info", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"]


# --------------------------
# Web service (local dev): same runtime as web, minus collectstatic.
# compose.yaml bind-mounts the repo over /app for the web service, so the
# baked-in COPY and collected static files below are shadowed anyway —
# running collectstatic here would just be wasted build time.
# --------------------------
FROM runtime-base AS dev

EXPOSE 8000

ENV PORT=8000
ENV DJANGO_SETTINGS_MODULE=progress_rpg.settings.dev

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "progress_rpg.asgi:application"]


# --------------------------
# Web service: Django ASGI server (must be last — Render builds final stage by default)
# --------------------------
FROM runtime-base AS web

EXPOSE 8000

ENV PORT=8000
ENV DJANGO_SETTINGS_MODULE=progress_rpg.settings.prod

RUN SECRET_KEY=dummy DATABASE_URL=postgres://dummy:dummy@localhost/dummy python manage.py collectstatic --noinput --clear

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "progress_rpg.asgi:application"]
