// hooks/useLogin.js
import { useCallback } from 'react';
import { API_BASE_URL } from '../config';

const API_URL = `${API_BASE_URL}/api/v1`;

export default function useLogin() {
  const login = useCallback(async (email, password, rememberMe = false) => {
    try {
      const response = await fetch(`${API_URL}/auth/jwt/create/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, remember_me: rememberMe }),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Login failed');
      }

      const rawBody = await response.text();
      const contentType = response.headers.get('content-type') || '';
      const data = rawBody && contentType.includes('application/json') ? JSON.parse(rawBody) : null;

      const accessToken = data?.access_token || data?.access;
      const refreshToken = data?.refresh_token || data?.refresh;

      if (!accessToken || !refreshToken) {
        const responsePreview = rawBody ? rawBody.slice(0, 160) : '<empty>';
        throw new Error(
          `Login endpoint returned an invalid response payload. url=${response.url} status=${response.status} contentType=${contentType || '<none>'} body=${responsePreview}`
        );
      }

      return {
        success: true,
        tokens: {
          access_token: accessToken,
          refresh_token: refreshToken,
        },
      };
    } catch (error) {
      console.error('[useLogin] Error logging in:', error);

      const message =
        typeof error === 'string'
          ? error.toLowerCase()
          : error?.message?.toLowerCase?.() || '';


      if (message.includes('no active account')) {
        return { success: false, error: 'Invalid email or password; please try again.' };
      } else {
        return {
          success: false,
          error: 'Login failed. Please try again.'
        };
      }
    }
  }, []);

  return login;
}
