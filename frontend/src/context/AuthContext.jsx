import { useEffect, useState } from 'react';
import { apiFetch } from "../utils/api";
import { AuthContext } from './authContext';
import { clearAuthStorage, getStoredAuthTokens, storeAuthTokens } from '../utils/authStorage';

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => getStoredAuthTokens().accessToken);
  const [refreshToken, setRefreshToken] = useState(() => getStoredAuthTokens().refreshToken);
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  // Use the centralized apiFetch here
  const authFetch = async (path, options = {}) => {
    return apiFetch(path, options);
  };

  useEffect(() => {
    async function verifyUser() {
      if (!accessToken || !refreshToken) {
        setLoading(false);
        setIsAuthenticated(false);
        return;
      }

      try {
        const data = await apiFetch('/me/');
        setUser(data);
        setIsAuthenticated(true);
      } catch {
        logout();
      } finally {
        setLoading(false);
      }
    }

    verifyUser();
  }, [accessToken, refreshToken]);

  const login = async (accessToken, refreshToken, options = {}) => {
    const { rememberMe = true } = options;
    storeAuthTokens(accessToken, refreshToken, rememberMe);
    setAccessToken(accessToken);
    setRefreshToken(refreshToken);
    setLoading(true);

    // Fetch user info after login
    try {
      const data = await apiFetch('/me/');
      //console.log("[AUTH PROVIDER] data:", data);
      setUser(data.user);
      setIsAuthenticated(true);
      return data;
    } catch {
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    clearAuthStorage();
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    setIsAuthenticated(false);
  };

  const value = {
    accessToken,
    refreshToken,
    isAuthenticated,
    user,
    setUser,
    login,
    logout,
    authFetch,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
