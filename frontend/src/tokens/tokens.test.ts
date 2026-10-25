import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import tamaguiConfig from '../../tamagui.config.ts';
import { renderTokens } from '../../scripts/generate-tokens.ts';
import {
  breakpoints,
  buttonVariants,
  color,
  listVariants,
  scale,
  semanticColor,
  spacing,
  textTone,
} from './index.ts';

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const rendered = renderTokens();

describe('generated token files', () => {
  // Same check as `npm run tokens:check` in CI, so it also fails locally.
  it.each([...rendered.keys()])('%s is up to date with src/tokens/', (file) => {
    expect(readFileSync(path.join(frontendDir, file), 'utf8')).toBe(rendered.get(file));
  });
});

describe('Sass output', () => {
  const colors = rendered.get('src/styles/tokens/_colors.scss')!;

  // Values the pre-#592 Sass (`color.adjust` on the base colour) compiled
  // to - the generated literals must stay exactly these.
  it.each([
    ['400', 'rgb(0%, 52.8431372549%, 21.6570234651%)'],
    ['600', 'rgb(0%, 37.8431372549%, 15.5094824815%)'],
  ])('keeps primary-scale %s identical to the previous Sass output', (step, expected) => {
    expect(colors).toContain(`  ${step}: ${expected},`);
  });

  it('keeps dark-scale 50 identical to the previous Sass output', () => {
    expect(colors).toContain('  50: rgb(31.4484503479%, 44.3137254902%, 57.1790006325%),');
  });

  // Sass parses these keys as numbers; quoting them would make the existing
  // map.get(..., 50) / map.get(..., 2xl) lookups silently return null.
  it('emits numeric-looking map keys unquoted', () => {
    expect(colors).toContain('\n  050: ');
    expect(colors).toContain('\n  000: ');
    expect(rendered.get('src/styles/tokens/_spacing.scss')).toContain('\n  2xl: 6rem');
    expect(colors).not.toMatch(/['"]\d+['"]:/);
  });
});

describe('runtime tokens', () => {
  const hex = /^#[0-9a-f]{6}([0-9a-f]{2})?$/;

  it('resolves every colour to hex', () => {
    const values = [
      ...Object.values(color),
      ...Object.values(scale).flatMap((steps) => Object.values(steps)),
      ...Object.values(semanticColor),
      ...Object.values(textTone).map((tone) => tone.color),
      ...Object.values(buttonVariants).flatMap((variant) =>
        Object.entries(variant)
          .filter(([key]) => key !== 'tone')
          .map(([, value]) => value),
      ),
    ];
    for (const value of values) expect(value).toMatch(hex);
  });

  it('leaves keyword colours and tone names alone', () => {
    expect(listVariants.default.bg).toBe('transparent');
    expect(listVariants.default.tone).toBe('base');
  });

  it('clips the out-of-gamut secondary-scale 050 to white (#857)', () => {
    expect(scale.secondary['050']).toBe('#ffffff');
    expect(semanticColor.colorBg).toBe('#ffffff');
  });

  it('keeps alpha in 8-digit hex', () => {
    expect(color.border).toBe('#00000026');
  });
});

describe('tamagui.config.ts', () => {
  it('builds its breakpoints from the breakpoint tokens', () => {
    expect(tamaguiConfig.media.sm).toEqual({ maxWidth: breakpoints.sm });
    expect(tamaguiConfig.media.md).toEqual({ maxWidth: breakpoints.md });
    expect(tamaguiConfig.media.mdUp).toEqual({ minWidth: breakpoints.md });
  });

  it('uses the app colour tokens instead of the stock palette', () => {
    expect(tamaguiConfig.tokens.color.primary400.val).toBe(scale.primary['400']);
    expect(tamaguiConfig.tokens.color.colorTextBody.val).toBe(semanticColor.colorTextBody);
    expect(tamaguiConfig.tokens.color).not.toHaveProperty('blue10Light');
  });

  it('keys the spacing scale by step, in scale order', () => {
    expect(tamaguiConfig.tokens.space['1'].val).toBe(spacing.xs);
    expect(tamaguiConfig.tokens.space['7'].val).toBe(spacing['3xl']);
    expect(tamaguiConfig.tokens.space.true.val).toBe(spacing.md);
  });
});
