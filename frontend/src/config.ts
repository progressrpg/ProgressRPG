// src/config.ts
export function resolveApiBaseUrl(): string {
  const rawEnvApiBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
  const envApiBaseUrl = typeof rawEnvApiBaseUrl === 'string'
    ? rawEnvApiBaseUrl.trim()
    : undefined;

  const base =
    (envApiBaseUrl && envApiBaseUrl.length > 0 ? envApiBaseUrl : undefined) ??
    (window.location.hostname === 'localhost'
      ? 'http://localhost:8000'
      : window.location.origin);

  return base.replace(/\/api\/v1\/?$/i, '').replace(/\/$/, '');
}

export const API_BASE_URL = resolveApiBaseUrl();
