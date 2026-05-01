import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import LoginPage from './LoginPage';

const mockNavigate = vi.fn();
const mockLoginWithJwt = vi.fn();
const mockAuthLogin = vi.fn();

vi.mock('../../hooks/useLogin', () => ({
  default: () => mockLoginWithJwt,
}));

vi.mock('../../context/useAuth', () => ({
  useAuth: () => ({
    login: mockAuthLogin,
  }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderLoginPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockLoginWithJwt.mockReset();
    mockAuthLogin.mockReset();
    mockAuthLogin.mockResolvedValue({});
  });

  it('submits without remember me by default', async () => {
    const user = userEvent.setup();
    mockLoginWithJwt.mockResolvedValue({
      success: true,
      tokens: {
        access_token: 'access-token',
        refresh_token: 'refresh-token',
      },
    });

    renderLoginPage();

    await user.type(screen.getByPlaceholderText('Email'), 'person@example.com');
    await user.type(screen.getByPlaceholderText('Password'), 'secret123');
    await user.click(screen.getByRole('button', { name: 'Log In' }));

    await waitFor(() => {
      expect(mockLoginWithJwt).toHaveBeenCalledWith('person@example.com', 'secret123', false);
    });
    expect(mockAuthLogin).toHaveBeenCalledWith('access-token', 'refresh-token', { rememberMe: false });
    expect(mockNavigate).toHaveBeenCalledWith('/timer');
  });

  it('submits remembered sessions when the checkbox is selected', async () => {
    const user = userEvent.setup();
    mockLoginWithJwt.mockResolvedValue({
      success: true,
      tokens: {
        access_token: 'access-token',
        refresh_token: 'refresh-token',
      },
    });

    renderLoginPage();

    await user.type(screen.getByPlaceholderText('Email'), 'person@example.com');
    await user.type(screen.getByPlaceholderText('Password'), 'secret123');
    await user.click(screen.getByRole('checkbox', { name: 'Remember me' }));
    await user.click(screen.getByRole('button', { name: 'Log In' }));

    await waitFor(() => {
      expect(mockLoginWithJwt).toHaveBeenCalledWith('person@example.com', 'secret123', true);
    });
    expect(mockAuthLogin).toHaveBeenCalledWith('access-token', 'refresh-token', { rememberMe: true });
  });
});
