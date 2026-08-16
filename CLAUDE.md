# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Progress RPG is a gamified productivity web app targeting people with ADHD. Users are paired with an in-game character that progresses alongside them as they complete real-world tasks. The core loop: start a task → run a timer → earn XP → character levels up.

## Tech Stack

- **Backend**: Django 5.2 + Django REST Framework, Celery (async tasks), Django Channels (WebSockets), PostgreSQL (PostGIS), Redis
- **Frontend**: React 19 + Vite, TanStack Query, Axios, SASS, Playwright (E2E + a11y)
- **Payments**: Stripe
- **Infra**: Docker / Render (`render.yaml`, `render-staging.yaml`)
- **Settings module**: `progress_rpg.settings.{base,dev,prod}` — dev is used in Docker/local

## Commands

### Backend

```bash
# Run with Docker (preferred for local dev — matches prod services)
docker compose up -d db redis
docker compose run --rm migrate
docker compose run --rm web python manage.py test            # all tests
docker compose run --rm web python manage.py test <app>.<TestClass>.<method>  # single test
docker compose down

# Run server locally (requires local postgres + redis)
python manage.py runserver
# Or via daphne (ASGI, supports WebSockets):
make run

# Migrations
python manage.py makemigrations
python manage.py migrate
```

### Frontend

```bash
cd frontend
npm run dev              # Vite dev server (port 5173)
npm run lint             # ESLint
npm run test             # Vitest unit tests
npx playwright test      # E2E tests
npm run build:production # Production build
```

Accessibility component patterns and a11y-specific test commands: `frontend/docs/ACCESSIBILITY.md`.

### Code Quality

Pre-commit hooks run Black, trailing-whitespace, and YAML checks on commit.

```bash
pre-commit install   # one-time setup
```

## Planning

When producing an implementation plan (plan mode, or any "planning only, don't implement" request), follow `.claude/plans/planning-template.md` — it defines the required sections, planning principles (reuse over new abstractions, justify concurrency controls, keep plans concise), and output format. Write finished plans into `.claude/plans/`.

## Deeper Reference

- **Architecture / app structure**: `docs/internal/backend-structure.md`
- **Why things are built this way**: `docs/internal/architectural-decisions.md`
- **Deploying**: `docs/internal/deployment-runbook.md`
- **Env vars / config**: `docs/internal/environment-and-configuration.md`
- **Frontend accessibility patterns**: `frontend/docs/ACCESSIBILITY.md`
- **GitHub Project field/option IDs, Notion page IDs**: `.claude/context/reference-ids.md`

## Conventions

- Use `503 Service Unavailable` for endpoints intentionally disabled/gated by a settings flag (kill switches, maintenance mode) — signals "temporarily down, safe to retry," consistent with `AsyncMaintenanceModeMiddleware` and `WaitlistSignupAPIView`. Reserve `403` for actual authorization failures.

### Branch/Deploy Strategy

- `development` → active dev branch; **base for feature-branch PRs** (not `staging`)
- `development` → `staging` via periodic PR (base `staging`, head `development`); deploys to staging
- `staging` → `main` via periodic PR (base `main`, head `staging`); `main` is the repo's default branch and deploys to production
- Full Render service names, env groups, and region: `docs/internal/deployment-runbook.md`

**Exception:** base a feature-branch PR on `staging` instead of `development` when the user says to — typically because their local dev tools are blocked (e.g. by Freedom) or the change can only be verified in a live/staging-like environment. Acknowledge the stated reason and use `staging` for that PR. This is a user call, not something to infer from the working environment (e.g. a Claude Code cloud/remote session lacking Docker is not by itself a reason to target `staging`). Otherwise, base feature-branch PRs on `development` as usual.

**Templates:** when creating a `development` → `staging` or `staging` → `main` PR, use the matching file in `.github/PULL_REQUEST_TEMPLATE/` (`development-to-staging.md` / `staging-to-main.md`) via `gh pr create -T <file>`, and fill in its UVI (user-visible improvement) bullets — non-technical, one line per user-facing change, grouped into Features / Fixes and UX improvements / Developer experience and quality (matching `.github/release.yml`'s categories). `development` → `staging` UVIs are written to be copy-pasted straight into the next `staging` → `main` release PR, so phrase them for that reuse up front rather than leaving them for later.
