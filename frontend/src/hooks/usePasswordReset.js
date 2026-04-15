import { useCallback } from 'react';
import { API_BASE_URL } from '../config';

const API_URL = `${API_BASE_URL}/api/v1/auth`;

async function readResponseJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function getErrorMessage(data, fallback) {
  if (!data || typeof data !== 'object') {
    return fallback;
  }

  const firstEntry = Object.values(data)[0];
  if (Array.isArray(firstEntry) && firstEntry[0]) {
    return firstEntry[0];
  }

  if (typeof data.detail === 'string' && data.detail) {
    return data.detail;
  }

  return fallback;
}

export default function usePasswordReset() {
  const requestPasswordReset = useCallback(async (email) => {
    try {
      const response = await fetch(`${API_URL}/password/reset/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await readResponseJson(response);

      if (!response.ok) {
        return {
          success: false,
          errors: data,
          errorMessage: getErrorMessage(data, 'Unable to send a reset link right now.'),
        };
      }

      return {
        success: true,
        message:
          data?.detail ||
          'If an account exists for that email, a password reset link has been sent.',
      };
    } catch (error) {
      console.error('[usePasswordReset] Unexpected request error:', error);
      return {
        success: false,
        errors: null,
        errorMessage: 'Unable to send a reset link right now.',
      };
    }
  }, []);

  const confirmPasswordReset = useCallback(async ({ uid, token, password1, password2 }) => {
    try {
      const response = await fetch(`${API_URL}/password/reset/confirm/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          uid,
          token,
          new_password1: password1,
          new_password2: password2,
        }),
      });

      const data = await readResponseJson(response);

      if (!response.ok) {
        return {
          success: false,
          errors: data,
          errorMessage: getErrorMessage(data, 'Unable to reset your password.'),
        };
      }

      return {
        success: true,
        message: data?.detail || 'Your password has been reset successfully.',
      };
    } catch (error) {
      console.error('[usePasswordReset] Unexpected confirm error:', error);
      return {
        success: false,
        errors: null,
        errorMessage: 'Unable to reset your password.',
      };
    }
  }, []);

  return { requestPasswordReset, confirmPasswordReset };
}
