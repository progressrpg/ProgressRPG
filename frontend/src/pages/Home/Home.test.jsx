import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import Home from './Home';

const mockNavigate = vi.fn();
const mockUseAuth = vi.fn();
const mockTrackEvent = vi.fn();

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../../utils/analytics', () => ({
  trackEvent: (...args) => mockTrackEvent(...args),
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
  let appendChildSpy;

  beforeEach(() => {
    mockNavigate.mockReset();
    mockUseAuth.mockReset();
    mockTrackEvent.mockReset();

    const originalAppendChild = document.body.appendChild.bind(document.body);
    appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation((node) => {
      if (node instanceof HTMLScriptElement) {
        return node;
      }

      return originalAppendChild(node);
    });
  });

  afterEach(() => {
    appendChildSpy?.mockRestore();
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

  it('only shows success after Mailchimp confirms the signup', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const user = userEvent.setup();
    const windowKeysBefore = new Set(Object.keys(window));

    renderHome();

    await user.type(screen.getByLabelText('Email address'), 'newperson@example.com');
    await user.click(screen.getByRole('button', { name: 'Join the waitlist' }));

    expect(screen.queryByText(/you’re on the list/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Submitting your email' })).toBeDisabled();

    const callbackName = Object.keys(window).find(
      (key) => !windowKeysBefore.has(key) && key.startsWith('mailchimpSignupCallback_')
    );

    expect(callbackName).toBeTruthy();

    window[callbackName]({
      result: 'success',
      msg: 'Thanks for subscribing!',
    });

    expect(await screen.findByRole('status')).toHaveTextContent('🎉 You’re on the list! We’ll be in touch soon.');
    expect(mockTrackEvent).toHaveBeenCalledWith('waitlist_signup_submitted', {
      form_name: 'mailchimp_waitlist',
      page: 'home',
    });
  });

  it('shows a Mailchimp error instead of a false success message', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const user = userEvent.setup();
    const windowKeysBefore = new Set(Object.keys(window));

    renderHome();

    await user.type(screen.getByLabelText('Email address'), 'existing@example.com');
    await user.click(screen.getByRole('button', { name: 'Join the waitlist' }));

    const callbackName = Object.keys(window).find(
      (key) => !windowKeysBefore.has(key) && key.startsWith('mailchimpSignupCallback_')
    );

    expect(callbackName).toBeTruthy();

    window[callbackName]({
      result: 'error',
      msg: '0 - Please enter a value',
    });

    expect(await screen.findByRole('alert')).toHaveTextContent('0 - Please enter a value');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(mockTrackEvent).not.toHaveBeenCalled();
  });

  it('treats already subscribed responses as a successful waitlist state', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const user = userEvent.setup();
    const windowKeysBefore = new Set(Object.keys(window));

    renderHome();

    await user.type(screen.getByLabelText('Email address'), 'existing@example.com');
    await user.click(screen.getByRole('button', { name: 'Join the waitlist' }));

    const callbackName = Object.keys(window).find(
      (key) => !windowKeysBefore.has(key) && key.startsWith('mailchimpSignupCallback_')
    );

    expect(callbackName).toBeTruthy();

    window[callbackName]({
      result: 'error',
      msg: '0 - existing@example.com is already subscribed to list Progress RPG.',
    });

    expect(await screen.findByRole('status')).toHaveTextContent(
      'You’re already on the list with that email address.'
    );
    expect(mockTrackEvent).toHaveBeenCalledWith('waitlist_signup_submitted', {
      form_name: 'mailchimp_waitlist',
      page: 'home',
    });
  });

  it('shows a hosted Mailchimp fallback when captcha verification is required', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const user = userEvent.setup();
    const windowKeysBefore = new Set(Object.keys(window));

    renderHome();

    await user.type(screen.getByLabelText('Email address'), 'person@gmail.com');
    await user.click(screen.getByRole('button', { name: 'Join the waitlist' }));

    const callbackName = Object.keys(window).find(
      (key) => !windowKeysBefore.has(key) && key.startsWith('mailchimpSignupCallback_')
    );

    expect(callbackName).toBeTruthy();

    window[callbackName]({
      result: 'redirect',
      msg: 'captcha',
    });

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Mailchimp needs one extra verification step to complete your signup.'
    );

    const hostedLink = screen.getByRole('link', { name: 'Continue to the secure signup form' });
    expect(hostedLink).toHaveAttribute(
      'href',
      expect.stringContaining('https://progressrpg.us13.list-manage.com/subscribe?')
    );
    expect(hostedLink).toHaveAttribute('href', expect.stringContaining('EMAIL=person%40gmail.com'));
    expect(mockTrackEvent).not.toHaveBeenCalled();
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
