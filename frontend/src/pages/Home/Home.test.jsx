import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import Home from './Home';

const mockNavigate = vi.fn();
const mockUseAuth = vi.fn();
const mockTrackEvent = vi.fn();
const mockRequestWaitlistSignup = vi.fn();

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../../utils/analytics', () => ({
  trackEvent: (...args) => mockTrackEvent(...args),
}));

vi.mock('../../hooks/useWaitlistSignup', () => ({
  default: () => ({
    requestWaitlistSignup: (...args) => mockRequestWaitlistSignup(...args),
  }),
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

function createDeferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });

  return { promise, resolve };
}

describe('Home', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockUseAuth.mockReset();
    mockTrackEvent.mockReset();
    mockRequestWaitlistSignup.mockReset();
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
    expect(mockRequestWaitlistSignup).not.toHaveBeenCalled();
  });

  it('shows a clear error when the waitlist form email is invalid', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const user = userEvent.setup();

    renderHome();

    await user.type(screen.getByLabelText('Email address'), 'not-an-email');
    await user.click(screen.getByRole('button', { name: 'Join the waitlist' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Enter a valid email address, like name@example.com.');
    expect(mockRequestWaitlistSignup).not.toHaveBeenCalled();
  });

  it('only shows success after the backend confirms the signup', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const user = userEvent.setup();
    const deferred = createDeferred();
    mockRequestWaitlistSignup.mockReturnValue(deferred.promise);

    renderHome();

    await user.type(screen.getByLabelText('Email address'), 'newperson@example.com');
    await user.click(screen.getByRole('button', { name: 'Join the waitlist' }));

    expect(mockRequestWaitlistSignup).toHaveBeenCalledWith('newperson@example.com');
    expect(screen.queryByText(/you'?re on the list/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Submitting your email' })).toBeDisabled();

    deferred.resolve({
      success: true,
      message: "You're on the list! We'll be in touch soon.",
    });

    expect(await screen.findByRole('status')).toHaveTextContent("You're on the list! We'll be in touch soon.");
    expect(mockTrackEvent).toHaveBeenCalledWith('waitlist_signup_submitted', {
      form_name: 'mailchimp_waitlist',
      page: 'home',
    });
  });

  it('shows the backend error instead of a false success message', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const user = userEvent.setup();
    mockRequestWaitlistSignup.mockResolvedValue({
      success: false,
      errorMessage: 'Unable to join the waitlist right now. Please try again later.',
    });

    renderHome();

    await user.type(screen.getByLabelText('Email address'), 'existing@example.com');
    await user.click(screen.getByRole('button', { name: 'Join the waitlist' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to join the waitlist right now. Please try again later.'
    );
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(mockTrackEvent).not.toHaveBeenCalled();
  });

  it('shows the backend success message for pending confirmation signups', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const user = userEvent.setup();
    mockRequestWaitlistSignup.mockResolvedValue({
      success: true,
      message: 'Check your email to confirm your place on the waitlist.',
      state: 'pending',
    });

    renderHome();

    await user.type(screen.getByLabelText('Email address'), 'person@example.com');
    await user.click(screen.getByRole('button', { name: 'Join the waitlist' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Check your email to confirm your place on the waitlist.'
    );
    expect(mockTrackEvent).toHaveBeenCalledWith('waitlist_signup_submitted', {
      form_name: 'mailchimp_waitlist',
      page: 'home',
    });
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
