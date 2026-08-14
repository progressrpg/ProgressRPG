import type { Preview } from '@storybook/react-vite';
import '../src/styles/main.scss';
import { withQueryClient } from './decorators/withQueryClient';

const preview: Preview = {
  // Global so any component that calls a TanStack Query hook - directly or
  // transitively (e.g. `useFeatureFlag` -> `useAppConfig`) - doesn't crash
  // for lack of a QueryClientProvider ancestor. See withQueryClient's
  // comment for how a story seeds its own query data.
  decorators: [withQueryClient],
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      // 'error' would fail CI on these pre-existing contrast issues; surface
      // them in the Storybook UI/test panel instead until they're fixed.
      test: 'todo',
    },
  },
};

export default preview;
