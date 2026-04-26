// main.jsx

import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

import App from './App';
import { AuthProvider } from './context/AuthContext';
import './styles/main.scss';

function canRenderReactQueryDevtools() {
  if (!import.meta.env.DEV || typeof navigator === 'undefined') {
    return false;
  }

  const locale = navigator.language || navigator.userLanguage;
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

const root = createRoot(document.getElementById('root'));
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
