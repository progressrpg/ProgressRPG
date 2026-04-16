import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import RegisterPage from './RegisterPage';

const mockRegister = vi.fn();

vi.mock('../../hooks/useRegister', () => ({
  default: () => ({
    register: mockRegister,
    characterAvailable: true,
  }),
}));

describe('RegisterPage', () => {
  let turnstileCallbacks;

  beforeEach(() => {
    vi.stubEnv('VITE_TURNSTILE_SITE_KEY', 'test-site-key');
    mockRegister.mockReset();
    mockRegister.mockResolvedValue({
      success: false,
      errors: {},
      errorMessage: 'Registration failed.',
    });

    turnstileCallbacks = {};
    window.turnstile = {
      render: vi.fn((container, options) => {
        turnstileCallbacks = options;
        container.dataset.rendered = 'true';
        return 'widget-id';
      }),
      remove: vi.fn(),
    };
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    delete window.turnstile;
  });

  it('renders Turnstile explicitly and submits the token with the form payload', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    );

    expect(window.turnstile.render).toHaveBeenCalledTimes(1);

    await user.type(screen.getByLabelText(/^Email:/i), 'new@example.com');
    await user.type(screen.getByLabelText(/^Password:/i), 'password123');
    await user.type(screen.getByLabelText(/^Confirm password:/i), 'password123');
    await user.type(screen.getByLabelText(/^Invite Code:/i), 'TESTER');
    await user.click(screen.getByRole('checkbox'));

    act(() => {
      turnstileCallbacks.callback('turnstile-token');
    });

    await user.click(screen.getByRole('button', { name: /create account/i }));

    expect(mockRegister).toHaveBeenCalledWith(
      'new@example.com',
      'password123',
      'password123',
      'TESTER',
      true,
      'turnstile-token',
      Intl.DateTimeFormat().resolvedOptions().timeZone
    );
  });
});
