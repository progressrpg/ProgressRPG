// PoC (issue #631): Tailwind config for the Gluestack/NativeWind PoC.
// `nativewind/preset` wires Tailwind's className strings through to
// react-native-web's style objects; without it, NativeWind's babel plugin
// has no matching Tailwind theme to resolve classes against.
import nativewindPreset from 'nativewind/preset';

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  presets: [nativewindPreset],
  theme: {
    extend: {},
  },
  plugins: [],
};
