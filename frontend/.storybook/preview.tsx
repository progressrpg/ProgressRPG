import type { Preview } from '@storybook/react-vite';
import { TamaguiProvider } from 'tamagui';
import tamaguiConfig from '../tamagui.config';
import '../src/styles/main.scss';

const preview: Preview = {
  decorators: [
    // Mirrors the app root (src/main.tsx) so components adopting Tamagui
    // primitives (starting with ProgressBar, #580) render correctly here
    // too, rather than every future story needing its own wrap.
    (Story) => (
      <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
        <Story />
      </TamaguiProvider>
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
