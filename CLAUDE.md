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

### Branch/Deploy Strategy

- `development` → active dev branch
- `staging` → base for PRs; deploys to staging via `render-staging.yaml`
- Production deploys via `render.yaml`
