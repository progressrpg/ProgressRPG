# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Testing

This project uses [Vitest](https://vitest.dev/) for unit testing React components.

### Running Tests

```bash
# Run all tests once
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

### Running Playwright tests

Playwright uses dedicated backend users instead of a personal account — every spec file that touches the activity timer gets its own user (see `playwright/testUser.ts`'s `TEST_USERS`), since the timer is a `OneToOneField` per player broadcast over one WebSocket channel, and sharing a user across concurrently-run spec files would race Start/Stop/label calls against each other. From the `frontend/` directory:

```bash
# Create or reset all dedicated E2E accounts (one per timer-touching spec file)
npm run test:e2e:setup-users

# Run the browser tests
npm run test:e2e
```

The base test credentials are:

- Email: `playwright@example.com`
- Password: `correcthorsebatterystaple`

Each spec-specific user is derived from the base email via plus-addressing (e.g. `playwright+timer@example.com`) and shares the base password. `npm run test:e2e:setup-user` (singular) still exists to seed just the base account if you need it directly.

The setup scripts run through `docker compose` so they match the backend test environment. You can override the defaults with `PLAYWRIGHT_TEST_EMAIL`, `PLAYWRIGHT_TEST_PASSWORD`, `PLAYWRIGHT_TEST_PLAYER_NAME`, `PLAYWRIGHT_TEST_CHARACTER_FIRST_NAME`, and `PLAYWRIGHT_TEST_CHARACTER_LAST_NAME` before running setup and Playwright.

### Writing Tests

Tests are located alongside their component files with the `.test.jsx` extension. For example:
- `Button.jsx` → `Button.test.jsx`
- `Input.jsx` → `Input.test.jsx`

We use [@testing-library/react](https://testing-library.com/react) for testing components.

Example test structure:
```javascript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import MyComponent from './MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

## Component documentation (Storybook)

Shared UI components are documented with [Storybook](https://storybook.js.org/). Stories live alongside their components as `*.stories.tsx` (e.g. `Button/Button.stories.tsx`) and appear under the `Shared/` section.

```bash
# Run Storybook locally (port 6006)
npm run storybook

# Build the static Storybook site (output: storybook-static/)
npm run build-storybook
```

Stories double as tests: interaction (`play`) functions and accessibility checks (via `@storybook/addon-a11y`) run through the Vitest browser integration:

```bash
# Run story tests headlessly in Chromium
npx vitest run --project=storybook

# Run only unit tests (excludes stories)
npx vitest run --project=unit
```

When adding a new shared component, add a story file covering its main variants; use a `play` function to assert interactive/accessibility behaviour (see `Button.stories.tsx` or `Input.stories.tsx` for examples).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
