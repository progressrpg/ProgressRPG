// hooks/useRegister.js
import { useCallback, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config';

const API_URL = `${API_BASE_URL}/api/v1`;

export default function useRegister() {
  const { login } = useAuth();
  const [characterAvailable, setCharacterAvailable] = useState(false);

  const register = useCallback(async (email, password1, password2, inviteCode, agreeToTerms, turnstileToken) => {
    try {
      const response = await fetch(`${API_URL}/auth/registration/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password1,
          password2,
          invite_code: inviteCode,
          agree_to_terms: agreeToTerms,
          turnstile_token: turnstileToken,
        }),
      });

      const data = await response.json();

      // Update character availability state here
      if (typeof data.characters_available === 'boolean') {
        setCharacterAvailable(data.characters_available);
      }

      if (!response.ok) {
        return {
          success: false,
          errors: data,
          errorMessage: data?.non_field_errors?.[0] || 'Registration failed.',
        }
      }

      if (data?.detail?.includes('Verification email sent')) {
        return {
          success: true,
          confirmationRequired: true,
          message: data.detail,
        };
      }

       // fallback: handle unexpected case (tokens returned)
      const { accessToken, refreshToken } = data;
      if (accessToken && refreshToken) {
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('refreshToken', refreshToken);
        await login(accessToken, refreshToken);
        return { success: true };
      }

      return {
        success: true,
        confirmationRequired: true,
        message: 'Please check your email to confirm your account.',
        availableCharacters: data.characters_available,
      };
    } catch (err) {
      console.error('[useRegister] Unexpected error:', err);
      return {
        success: false,
        errors: null,
        errorMessage: 'Something went wrong, please try again.',
      };
    }
  }, [login]);
  return { register, characterAvailable };
}
