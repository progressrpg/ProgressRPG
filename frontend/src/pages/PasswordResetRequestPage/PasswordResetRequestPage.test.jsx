import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import PasswordResetRequestPage from './PasswordResetRequestPage';

describe('PasswordResetRequestPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = vi.fn();
  });

  it('submits the reset request and shows a success message', async () => {
    const user = userEvent.setup();

    globalThis.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ detail: 'Password reset e-mail has been sent.' }),
    });

    render(
      <MemoryRouter>
        <PasswordResetRequestPage />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/email/i), 'player@example.com');
    await user.click(screen.getByRole('button', { name: 'Send reset link' }));

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/password/reset/'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email: 'player@example.com' }),
      })
    );

    expect(screen.getByText('Password reset e-mail has been sent.')).toBeInTheDocument();
  });
});
