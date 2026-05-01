const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';

function getTokenBundle(storage) {
  const accessToken = storage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = storage.getItem(REFRESH_TOKEN_KEY);

  if (!accessToken || !refreshToken) {
    return null;
  }

  return { accessToken, refreshToken };
}

export function getStoredAuthTokens() {
  return getTokenBundle(localStorage) || getTokenBundle(sessionStorage) || {
    accessToken: null,
    refreshToken: null,
  };
}

export function storeAuthTokens(accessToken, refreshToken, rememberMe = true) {
  clearAuthStorage();
  const storage = rememberMe ? localStorage : sessionStorage;

  storage.setItem(ACCESS_TOKEN_KEY, accessToken);
  storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function updateStoredAccessToken(accessToken) {
  if (localStorage.getItem(REFRESH_TOKEN_KEY)) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    return;
  }

  if (sessionStorage.getItem(REFRESH_TOKEN_KEY)) {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  }
}

export function getStoredAccessToken() {
  return getStoredAuthTokens().accessToken;
}

export function clearAuthStorage() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}
