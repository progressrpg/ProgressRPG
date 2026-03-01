// hooks/useLogin.js
import { useCallback } from 'react';
import { API_BASE_URL } from '../config';

const API_URL = `${API_BASE_URL}/api/v1`;

export default function useLogin() {
  const login = useCallback(async (email, password) => {
    try {
      const response = await fetch(`${API_URL}/auth/jwt/create/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Login failed');
      }

      const rawBody = await response.text();
      const data = rawBody ? JSON.parse(rawBody) : null;

      if (!data?.access_token || !data?.refresh_token) {
        throw new Error('Login endpoint returned an invalid response payload.');
      }

      //console.log('useLogin, data:', data);
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);

      return { success: true, tokens: data };
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
