import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PasswordResetConfirmPage from './PasswordResetConfirmPage';

describe('PasswordResetConfirmPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn();
  });

  it('shows an invalid-link message when the key is malformed', () => {
    render(
      <MemoryRouter initialEntries={['/reset-password/invalid']}>
        <Routes>
          <Route path="/reset-password/:key" element={<PasswordResetConfirmPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: 'Invalid reset link' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Update password' })).not.toBeInTheDocument();
  });

  it('submits the new password using the parsed reset key', async () => {
    const user = userEvent.setup();

    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ detail: 'Password has been reset with the new password.' }),
    });

    render(
      <MemoryRouter initialEntries={['/reset-password/MQ-set-password-token123']}>
        <Routes>
          <Route
            path="/reset-password/:key"
            element={<PasswordResetConfirmPage />}
          />
        </Routes>
      </MemoryRouter>
    );

    await user.type(screen.getByPlaceholderText('New password'), 'new-password-123');
    await user.type(
      screen.getByPlaceholderText('Confirm new password'),
      'new-password-123'
    );
    await user.click(screen.getByRole('button', { name: 'Update password' }));

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/password/reset/confirm/'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          uid: 'MQ',
          token: 'set-password-token123',
          new_password1: 'new-password-123',
          new_password2: 'new-password-123',
        }),
      })
    );

    expect(
      screen.getByText('Password has been reset with the new password.')
    ).toBeInTheDocument();
  });
});
