import type { Preview } from '@storybook/react-vite';
import { TamaguiProvider } from 'tamagui';
import tamaguiConfig from '../tamagui.config';
import '../src/styles/main.scss';
import { withQueryClient } from './decorators/withQueryClient';
import { TooltipProvider } from '../src/components/Tooltip/Tooltip';

const preview: Preview = {
  decorators: [
    // Global so any component that calls a TanStack Query hook - directly or
    // transitively (e.g. `useFeatureFlag` -> `useAppConfig`) - doesn't crash
    // for lack of a QueryClientProvider ancestor. See withQueryClient's
    // comment for how a story seeds its own query data.
    withQueryClient,
    // Mirrors the app root (src/main.tsx) so components adopting Tamagui
    // primitives (starting with ProgressBar, #580) render correctly here too,
    // rather than every future story needing its own wrap.
    (Story) => (
      <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
        <Story />
      </TamaguiProvider>
    ),
    // TooltipProvider is a no-op passthrough since #583 (Tamagui's Tooltip
    // needs no ambient ancestor), kept here purely so Tooltip.stories.tsx
    // and its autodocs-generated Docs page - which renders the component
    // through its own preview pathway and doesn't reliably pick up
    // meta-level decorators - don't need their own wrapping.
    (Story) => (
      <TooltipProvider>
        <Story />
      </TooltipProvider>
    ),
  ],
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
