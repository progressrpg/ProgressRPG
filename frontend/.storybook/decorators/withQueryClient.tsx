import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Decorator } from '@storybook/react-vite';

/**
 * Wraps a story in a fresh `QueryClient` per render, so components that call
 * TanStack Query hooks (`useQuery`/`useQueryClient`) don't crash outside a
 * provider. Retries are disabled - Storybook has no real API to fetch from,
 * so a failed request should render its empty/error state immediately
 * rather than retrying for several seconds.
 *
 * Seed data for a specific query (so a component renders populated instead
 * of loading/empty) via a story's own decorator + `queryClient.setQueryData`,
 * see `EntitySearchInput.stories.tsx` / `TutorialModal.stories.tsx`.
 */
export const withQueryClient: Decorator = (Story) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <Story />
    </QueryClientProvider>
  );
};
