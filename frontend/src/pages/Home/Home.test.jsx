import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import Home from './Home';

const mockNavigate = vi.fn();
const mockUseAuth = vi.fn();

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>
  );
}

describe('Home', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockUseAuth.mockReset();
  });

  it('renders the logged-out landing page', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });

    renderHome();

    expect(screen.getByRole('heading', { name: 'Turn effort into momentum' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Join the waiting list' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Quick links' })).toBeInTheDocument();
    expect(screen.getByLabelText('Email address')).toBeInTheDocument();
    expect(screen.getByText('Only your email is required. We will use it for early-access and product updates.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Join the waitlist' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back to top' })).toBeInTheDocument();
  });

  it('shows a clear error when the waitlist form is submitted without an email', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const user = userEvent.setup();

    renderHome();

    await user.click(screen.getByRole('button', { name: 'Join the waitlist' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Enter an email address to join the waitlist.');
    expect(screen.getByLabelText('Email address')).toHaveAttribute('aria-invalid', 'true');
  });

  it('shows a clear error when the waitlist form email is invalid', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const user = userEvent.setup();

    renderHome();

    await user.type(screen.getByLabelText('Email address'), 'not-an-email');
    await user.click(screen.getByRole('button', { name: 'Join the waitlist' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Enter a valid email address, like name@example.com.');
  });

  it('redirects authenticated users to the game', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, loading: false });

    const { container } = renderHome();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/game', { replace: true });
    });
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing while auth is still loading', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: true });

    const { container } = renderHome();

    expect(container).toBeEmptyDOMElement();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
