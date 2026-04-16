import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
    expect(screen.getByRole('button', { name: 'Join the waitlist' })).toBeInTheDocument();
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
