// PoC (Restyle): adapted subset of Button.test.tsx's cases, matching the
// same reduced scope the Tamagui/Gluestack PoCs' Button ports used
// (children/variant/disabled/onClick only - `as`/`icon`/arbitrary
// className passthrough weren't ported, same as those two PoCs).
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from '@shopify/restyle';

import ButtonRestyle from './Button.restyle';
import restyleTheme from '../../restyle-theme';

function renderButton(props: React.ComponentProps<typeof ButtonRestyle> = {}) {
  return render(
    <ThemeProvider theme={restyleTheme}>
      <ButtonRestyle {...props}>Click me</ButtonRestyle>
    </ThemeProvider>
  );
}

describe('Button (Restyle PoC)', () => {
  it('renders children content', () => {
    renderButton();
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });

  it('applies the primary variant background color by default', () => {
    renderButton();
    const button = screen.getByRole('button');
    expect(getComputedStyle(button).backgroundColor).toBe('rgb(0, 122, 50)');
  });

  it('applies the secondary variant background color', () => {
    renderButton({ variant: 'secondary' });
    const button = screen.getByRole('button');
    expect(getComputedStyle(button).backgroundColor).toBe('rgb(231, 255, 241)');
  });

  it('applies the danger variant background color', () => {
    renderButton({ variant: 'danger' });
    const button = screen.getByRole('button');
    expect(getComputedStyle(button).backgroundColor).toBe('rgb(198, 40, 40)');
  });

  it('sets the native disabled attribute', () => {
    renderButton({ disabled: true });
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('calls onClick when pressed', async () => {
    let clicked = false;
    renderButton({ onClick: () => { clicked = true; } });
    screen.getByRole('button').click();
    expect(clicked).toBe(true);
  });
});
