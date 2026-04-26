# Copilot Instructions for ProgressRPG

## Project Overview

ProgressRPG is a multiplayer body-doubling RPG that helps users stay productive by pairing them with in-game characters who progress alongside them. The project combines a Django REST API backend with a React frontend to create an immersive gamified productivity experience.

### Tech Stack

**Backend:**
- Django 5.2+ with Django REST Framework
- Celery for async task processing
- Django Channels for WebSocket support
- PostgreSQL database
- Redis for caching and Celery broker
- Stripe for payments

**Frontend:**
- React 19 with Vite
- React Router for navigation
- TanStack Query (React Query) for data fetching
- Axios for API calls
- SASS for styling
- Playwright for E2E testing

## Project Structure

### Backend Apps

- `api/` - Core API endpoints and serializers
- `character/` - Character management (models, views, serializers)
- `progression/` - Skill progression, activities, and leveling system
- `gameplay/` - Game mechanics and quest systems
- `gameworld/` - World building, locations, and environments
- `locations/` - Specific location management
- `events/` - Event system for game events
- `users/` - User authentication and profiles
- `payments/` - Payment processing with Stripe
- `server_management/` - Server administration tools
- `progress_rpg/` - Main Django project settings

### Frontend Structure

- `frontend/src/components/` - Reusable React components
- `frontend/src/pages/` - Page-level components
- `frontend/src/layout/` - Layout components
- `frontend/src/api/` - API client functions
- `frontend/src/hooks/` - Custom React hooks
- `frontend/src/context/` - React context providers
- `frontend/src/routes/` - Routing configuration
- `frontend/src/websockets/` - WebSocket client logic
- `frontend/src/styles/` - SASS stylesheets

## Coding Standards

### Python/Django

1. **Code Style:**
   - Use Black for code formatting (configured in `.pre-commit-config.yaml`)
   - Follow PEP 8 conventions
   - Use type hints where applicable (mypy is configured)

2. **Django Patterns:**
   - Keep business logic in models and utilities
   - Use Django REST Framework serializers for API responses
   - Create custom managers for complex queries
   - Use Django signals for cross-app communication (see `character/signals.py`)
   - Keep views thin - delegate to services/utilities

3. **Models:**
   - Use clear, descriptive model names
   - Add `__str__` methods to all models
   - Use `related_name` for foreign keys
   - Add verbose names and help text

4. **Testing:**
   - Write tests in `tests.py` or `tests/` directory
   - Use Django's TestCase or DRF's APITestCase
   - Test business logic, not Django internals

### JavaScript/React

1. **Code Style:**
   - Use ESLint (configured in `eslint.config.js`)
   - Use functional components with hooks
   - Follow React best practices for component composition

2. **React Patterns:**
   - Use TanStack Query for server state management
   - Custom hooks for reusable logic (in `hooks/`)
   - Context for global state (in `context/`)
   - Components should be focused and single-purpose

3. **File Naming:**
   - Use PascalCase for component files (`.jsx`)
   - Use camelCase for utility files (`.js`)

4. **Testing:**
   - Use Playwright for E2E tests (configured)
   - Test user flows and critical paths

## Development Workflow

### Setting Up the Environment

**Backend:**
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Running Tests

- When developing locally, prefer running backend and integration-style tests through Docker/`compose.yaml` so PostgreSQL, Redis, and other services match the expected app environment.

**Backend:**
```bash
docker compose up -d db redis
docker compose run --rm migrate
docker compose run --rm web python manage.py test
docker compose down
```

**Frontend:**
```bash
cd frontend
npm run lint
npx playwright test
```

### Code Quality

- Pre-commit hooks are configured for Python (Black, trailing whitespace, YAML checks)
- Run `pre-commit install` to enable automatic checks
- ESLint runs on frontend code via `npm run lint`

### Database Migrations

- Always create migrations after model changes: `python manage.py makemigrations`
- Review migration files before committing
- Use descriptive migration names
- Test migrations in both directions (migrate and rollback)

## Key Conventions

### API Design

- Use RESTful conventions for endpoints
- Version APIs when making breaking changes
- Use DRF serializers for validation
- Return appropriate HTTP status codes
- Use filters for list endpoints (see `filters.py` files)

### WebSocket Communication

- WebSocket endpoints are handled via Django Channels
- Connection logic in `frontend/src/websockets/`
- Use JWT authentication for WebSocket connections

### Environment Configuration

- Use `django-environ` for settings management
- Environment-specific settings in `progress_rpg/settings/`
- Never commit secrets or credentials

### Feature Flags

- Feature flags configuration in `frontend/src/featureFlags.js`
- Use for gradual rollout and A/B testing

## Common Tasks

### Adding a New Django App

1. Create app: `python manage.py startapp <app_name>`
2. Add to `INSTALLED_APPS` in settings
3. Create models, views, serializers
4. Register admin if needed
5. Create URL patterns
6. Run migrations

### Adding a New Frontend Component

1. Create component in appropriate directory under `components/` or `pages/`
2. Follow existing component patterns
3. Use TanStack Query for data fetching
4. Add to routing if it's a page

### Working with Celery Tasks

- Define tasks in `tasks.py` within each app
- Use `@shared_task` decorator
- Test tasks synchronously in development: `task.apply()`

## Documentation

- Sphinx documentation in `docs/` directory
- Error codes documented in `docs/error_codes.txt`
- Keep README.md updated with major changes

## Deployment

- Render deployment configuration lives in `render.yaml` and `render-staging.yaml`
- Docker support available (see `Dockerfile` and `compose.yaml`)
- Static files handled by WhiteNoise
- Frontend builds via Vite: `npm run build:production`

## Security

- CSRF protection enabled
- JWT authentication for API and WebSockets
- Django's security middleware configured
- Rate limiting via django-ratelimit
- CORS configured via django-cors-headers

## Best Practices

1. **Make minimal changes** - Only modify what's necessary
2. **Test thoroughly** - Run both backend and frontend tests
3. **Follow existing patterns** - Look at similar code in the codebase
4. **Document complex logic** - Add comments for non-obvious code
5. **Keep dependencies updated** - Use `pip-tools` for Python, npm for JavaScript
6. **Security first** - Always consider security implications
7. **Performance matters** - Use database indexes, optimize queries, minimize API calls

## When Making Changes

- Check for existing similar implementations first
- Run linters and formatters before committing
- Update tests to cover new functionality
- Ensure migrations are created for model changes
- Test in both development and production-like environments
- Consider backwards compatibility for API changes
