// src/config.ts
function resolveApiBaseUrl(): string {
  const envApiBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;

  const base =
    envApiBaseUrl ??
    (window.location.hostname === 'localhost'
      ? 'http://localhost:8000'
      : window.location.origin);

  return base.replace(/\/api\/v1\/?$/i, '').replace(/\/$/, '');
}

export const API_BASE_URL = resolveApiBaseUrl();
