// main.tsx

import React from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

import App from './App';
import { AuthProvider } from './context/AuthContext';
import './styles/tailwind.css';
import './styles/main.scss';

function canRenderReactQueryDevtools(): boolean {
  if (!import.meta.env.DEV || typeof navigator === 'undefined') {
    return false;
  }

  const locale = navigator.language || (navigator as Navigator & { userLanguage?: string }).userLanguage;
  if (!locale || typeof Intl?.Locale !== 'function') {
    return true;
  }

  try {
    new Intl.Locale(locale);
    return true;
  } catch {
    return false;
  }
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

// eslint-disable-next-line @typescript-eslint/no-non-null-assertion
const root = createRoot(document.getElementById('root')!);
root.render(
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <App />
    </AuthProvider>
    {canRenderReactQueryDevtools() && (
      <ReactQueryDevtools initialIsOpen={false} />
    )}
  </QueryClientProvider>
);
