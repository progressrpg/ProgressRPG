#!/usr/bin/env bash
# One-time / repeatable local dev environment setup for Progress RPG.
# Mirrors the workflow documented in CLAUDE.md: Docker-based backend
# (Django + Postgres/PostGIS + Redis), Vite frontend, pre-commit hooks.
set -euo pipefail

cd "$(dirname "$0")/.."

info()  { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m!!\033[0m %s\n' "$1"; }
fail()  { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------
info "Checking prerequisites"

command -v docker >/dev/null 2>&1 || fail "Docker is required. Install it from https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required (the 'docker compose' subcommand)."
command -v node >/dev/null 2>&1 || fail "Node.js is required for the frontend. Install it from https://nodejs.org/"
command -v npm >/dev/null 2>&1 || fail "npm is required for the frontend."

echo "docker:  $(docker --version)"
echo "compose: $(docker compose version --short 2>/dev/null || echo unknown)"
echo "node:    $(node --version)"
echo "npm:     $(npm --version)"

# ---------------------------------------------------------------------------
# 2. Local .env
# ---------------------------------------------------------------------------
# compose.yaml points web/celery/celery-beat/migrate at env_file: .env.
# Settings (progress_rpg/settings/base.py) fall back to sane defaults for
# everything, so an empty/minimal file is enough to get a working local
# environment; fill in real secrets (Stripe, email, Sentry, etc.) as needed.
if [ ! -f .env ]; then
  info "Creating local .env (not committed — see .gitignore)"
  cat > .env <<'EOF'
DJANGO_SETTINGS_MODULE=progress_rpg.settings.dev
DEBUG=True
EOF
else
  info ".env already exists, leaving it as-is"
fi

# ---------------------------------------------------------------------------
# 3. Backend: db + redis, then migrations (docker compose, per CLAUDE.md)
# ---------------------------------------------------------------------------
info "Starting db and redis containers"
docker compose up -d db redis

info "Running database migrations"
docker compose run --rm migrate

# ---------------------------------------------------------------------------
# 4. Pre-commit hooks (Black, trailing-whitespace, YAML checks)
# ---------------------------------------------------------------------------
info "Setting up pre-commit hooks"
PYTHON_BIN="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON_BIN" ]; then
  warn "No local Python found — skipping 'pre-commit install'. Backend itself runs fine via Docker."
elif command -v pre-commit >/dev/null 2>&1; then
  pre-commit install
elif "$PYTHON_BIN" -m pip install --user pre-commit >/dev/null 2>&1 && "$PYTHON_BIN" -m pre_commit install; then
  :
else
  warn "Could not install pre-commit locally — run 'pip install pre-commit && pre-commit install' manually."
fi

# ---------------------------------------------------------------------------
# 5. Frontend dependencies
# ---------------------------------------------------------------------------
info "Installing frontend dependencies"
(cd frontend && npm install)

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
info "Setup complete"
cat <<'EOF'

Next steps:

  Start the full backend stack (web + celery + celery-beat + db + redis):
    docker compose up

  Run backend tests:
    docker compose run --rm web python manage.py test

  Run a single test:
    docker compose run --rm web python manage.py test <app>.<TestClass>.<method>

  Start the frontend dev server (in another terminal):
    cd frontend && npm run dev
    # -> http://localhost:5173

  Stop the stack:
    docker compose down

EOF
