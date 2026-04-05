# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12

# --------------------------
# Python runtime stage
# --------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app
ENTRYPOINT ["/app/entrypoint.sh"]

ARG UID=1000
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/bin/bash" \
    --uid "${UID}" \
    appuser
RUN mkdir -p /home/appuser && chown -R appuser:appuser /home/appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gdal-bin \
        libgdal-dev \
        build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .
COPY --chmod=755 entrypoint.sh /app/entrypoint.sh


RUN mkdir -p /app/staticfiles \
    && chown -R appuser:appuser /app/staticfiles

USER appuser

ENV SECRET_KEY=dummy-build-secret-key
RUN python manage.py collectstatic --noinput

EXPOSE 8000
ENV PATH="/usr/local/bin:$PATH"
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "progress_rpg.asgi:application"]

# --------------------------
# Service-specific targets
# --------------------------
FROM runtime AS web
CMD ["sh", "-c", "daphne -b 0.0.0.0 -p 8000 progress_rpg.asgi:application"]

FROM runtime AS celery
CMD ["celery", "-A", "progress_rpg", "worker", "--loglevel=info"]

FROM runtime AS celery-beat
CMD ["celery", "-A", "progress_rpg", "beat", "--loglevel=info", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"]
