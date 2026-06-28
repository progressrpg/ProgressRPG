# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Component documentation (Storybook)

From the `frontend/` directory:

```bash
# Start Storybook locally
npm run storybook

# Build static Storybook docs
npm run build-storybook
```

Storybook documents shared components and their props under `src/components/**/*.stories.tsx`.

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

Playwright uses a dedicated backend user instead of a personal account. From the `frontend/` directory:

```bash
# Create or reset the dedicated E2E account
npm run test:e2e:setup-user

# Run the browser tests
npm run test:e2e
```

The default test credentials are:

- Email: `playwright@example.com`
- Password: `correcthorsebatterystaple`

The setup script runs through `docker compose` so it matches the backend test environment. You can override the defaults with `PLAYWRIGHT_TEST_EMAIL`, `PLAYWRIGHT_TEST_PASSWORD`, `PLAYWRIGHT_TEST_PLAYER_NAME`, `PLAYWRIGHT_TEST_CHARACTER_FIRST_NAME`, and `PLAYWRIGHT_TEST_CHARACTER_LAST_NAME` before running the setup command and Playwright.

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

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
