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

# Django shell inside Docker
make ps

# psql inside Docker
make ds

# Stripe webhook listener (local dev)
make stripelistener
```

### Frontend

```bash
cd frontend
npm run dev              # Vite dev server (port 5173)
npm run lint             # ESLint
npm run test             # Vitest unit tests
npm run test:ui          # Vitest with UI
npm run test:coverage    # Coverage report
npx playwright test                      # All E2E tests
npm run test:a11y                        # Accessibility tests only
npm run build:production                 # Production build
```

### Code Quality

Pre-commit hooks run Black, trailing-whitespace, and YAML checks on commit.

```bash
pre-commit install   # one-time setup
```

## Planning

When producing an implementation plan (plan mode, or any "planning only, don't implement" request), follow `.claude/plans/planning-template.md` — it defines the required sections, planning principles (reuse over new abstractions, justify concurrency controls, keep plans concise), and output format. Write finished plans into `.claude/plans/`.

## GitHub Project — Backlog

The main project board is **Backlog** (org `progressrpg`, project number `3`), a holding space for everything not required for the MVP (see the project README for full philosophy — capture non-MVP ideas here, don't act on them immediately).

- **Project ID**: `PVT_kwDOD79Q6c4BVbBV`
- **URL**: https://github.com/orgs/progressrpg/projects/3
- **Owner**: `progressrpg` (organization) — use `--owner progressrpg` with `gh project` commands
- Repo `progressrpg/ProgressRPG` is a separate `gh` context; use `gh project item-add 3 --owner progressrpg --url <issue-url>` to add issues to this board.
- Note: `gh project list --owner progressrpg` only surfaces org-owned projects; there's also a personal-account project set under `--owner gaidheal1` (e.g. "Progress Phase 2", #7) — don't confuse the two when listing/searching projects.

### Fields (field-list output, `gh project field-list 3 --owner progressrpg`)

| Field | ID | Type | Options (id → name) |
|---|---|---|---|
| Title | `PVTF_lADOD79Q6c4BVbBVzhQ27hY` | text | — |
| Assignees | `PVTF_lADOD79Q6c4BVbBVzhQ27hc` | text | — |
| Status | `PVTSSF_lADOD79Q6c4BVbBVzhQ27hg` | single-select | `f75ad846`→Backlog, `e18bf179`→Ready, `47fc9ee4`→In progress, `aba860b9`→Staging review, `98236657`→Done |
| Labels | `PVTF_lADOD79Q6c4BVbBVzhQ27hk` | text | — |
| Linked pull requests | `PVTF_lADOD79Q6c4BVbBVzhQ27ho` | text | — |
| Milestone | `PVTF_lADOD79Q6c4BVbBVzhQ27hs` | text | — |
| Repository | `PVTF_lADOD79Q6c4BVbBVzhQ27hw` | text | — |
| Reviewers | `PVTF_lADOD79Q6c4BVbBVzhQ27h4` | text | — |
| Parent issue | `PVTF_lADOD79Q6c4BVbBVzhQ27h8` | text | — |
| Sub-issues progress | `PVTF_lADOD79Q6c4BVbBVzhQ27iA` | text | — |
| Created | `PVTF_lADOD79Q6c4BVbBVzhQ27iE` | date | — |
| Updated | `PVTF_lADOD79Q6c4BVbBVzhQ27iI` | date | — |
| Closed | `PVTF_lADOD79Q6c4BVbBVzhQ27iM` | date | — |
| Priority | `PVTSSF_lADOD79Q6c4BVbBVzhQ27lk` | single-select | `79628723`→P0, `0a877460`→P1, `da944a9c`→P2 |
| Size | `PVTSSF_lADOD79Q6c4BVbBVzhQ27lo` | single-select | `911790be`→XS, `b277fb01`→S, `86db8eb3`→M, `853c8207`→L, `2d0801e2`→XL |
| Estimate | `PVTF_lADOD79Q6c4BVbBVzhQ27ls` | number | — |
| Iteration | `PVTIF_lADOD79Q6c4BVbBVzhQ27lw` | iteration | — |

To set a single-select field on an item: `gh project item-edit --id <ITEM_ID> --field-id <FIELD_ID> --project-id PVT_kwDOD79Q6c4BVbBV --single-select-option-id <OPTION_ID>`. Get an item's ID via `gh project item-list 3 --owner progressrpg --format json`.

## Architecture

### Backend Apps

All API routes live under `/api/v1/` (see `api/urls.py`) using DRF routers:

| App | Purpose |
|---|---|
| `api/` | Core API endpoints, auth (JWT via dj-rest-auth + simplejwt), registration |
| `character/` | Character model, `PlayerCharacterLink` (user↔character pairing), Behaviour |
| `progression/` | Skills, activities (`PlayerActivity`, `CharacterActivity`), leveling, XP |
| `gameplay/` | `QuestTimer`, `ActivityTimer`, WebSocket consumer (`TimerConsumer`), XP modifiers |
| `gameworld/` | World/location data |
| `locations/` | `PopulationCentre` (map data) |
| `events/` | Game event system |
| `users/` | `Player` model (extends auth user), player views |
| `payments/` | Stripe webhook + checkout flow |
| `server_management/` | Maintenance mode, admin utilities |
| `progress_rpg/` | Django project settings, ASGI config, middleware |

**Key cross-app wiring:**
- `character/signals.py` creates `QuestTimer` and `Behaviour` when a `Character` is saved, and recomputes `can_link` flags on `PlayerCharacterLink` changes
- Business logic lives in `models.py` and `services/`; views stay thin
- Celery tasks defined per-app in `tasks.py` using `@shared_task`

**WebSocket:** `gameplay/consumers.py` → `TimerConsumer` handles the real-time timer. Route: `ws/profile_<id>/`. Authenticated via JWT.

**API docs:** `/api/docs/` (Swagger) and `/api/schema/` (OpenAPI) via drf-spectacular.

### Frontend

React SPA served separately (port 5173 in dev, built via Vite for prod).

| Directory | Purpose |
|---|---|
| `src/context/` | `AuthContext` (JWT tokens in localStorage), `GameContext`, `WebSocketContext`, `ToastContext`, `MaintenanceContext` |
| `src/api/` | Axios API client functions |
| `src/hooks/` | Custom React hooks (TanStack Query wrappers) |
| `src/pages/` | Page-level components (one per route) |
| `src/components/` | Reusable UI components |
| `src/routes/` | `routesConfig.jsx` (route definitions), `routePaths.js` (path constants), `AppRoutes.jsx` |
| `src/websockets/` | WebSocket client logic |
| `src/featureFlags.js` | Feature flags (`'no'` / `'all'` / `'premium'`) |

**Auth flow:** `AuthContext` stores JWT access/refresh tokens in `localStorage`. `apiFetch` in `src/utils/api.js` handles token refresh automatically.

**State:** TanStack Query manages server state. React Context handles global UI state (auth, game, websocket, toasts).

## Conventions

- Use `503 Service Unavailable` for endpoints intentionally disabled/gated by a settings flag (kill switches, maintenance mode) — signals "temporarily down, safe to retry," consistent with `AsyncMaintenanceModeMiddleware` and `WaitlistSignupAPIView`. Reserve `403` for actual authorization failures.

### Branch/Deploy Strategy

- `development` → active dev branch; **base for feature-branch PRs** (not `staging`)
- `development` → `staging` via periodic PR (base `staging`, head `development`); deploys to staging via `render-staging.yaml` (services `web-staging`/`celery-staging`/`celery-beat-staging`, env group "Staging env")
- `staging` → `main` via periodic PR (base `main`, head `staging`); `main` is the repo's default branch and deploys to production via `render.yaml` (services `web`/`celery`/`celery-beat`, env group "Prod env")
- Repo: `progressrpg/ProgressRPG` (org `progressrpg`), region `frankfurt` for all Render services

**Exception:** base a feature-branch PR on `staging` instead of `development` when either:
- local dev tooling isn't available in the working environment (e.g. no Docker/Postgres/Redis access, so the change can't be run or tested locally), or
- the change only manifests in a live/staging-like environment (e.g. deploy config, webhook integrations, anything that can't be meaningfully verified against `development` alone).

Otherwise, base feature-branch PRs on `development` as usual.
