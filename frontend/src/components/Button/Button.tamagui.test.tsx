import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';

import ButtonTamagui from './Button.tamagui';
import tamaguiConfig from '../../../tamagui.config';

function renderButton(ui: React.ReactElement) {
  return render(<TamaguiProvider config={tamaguiConfig}>{ui}</TamaguiProvider>);
}

// PoC note (issue #629): the original Button.test.tsx asserts variants via
// `button.className` containing the variant name - that works because CSS
// Modules preserve the source class name in the hashed output. Tamagui's
// compiler instead emits atomic, content-hashed class names with no
// relationship to `appVariant`'s value, so that assertion strategy doesn't
// carry over; asserting computed background-color is the Tamagui-compatible
// equivalent.
describe('Button (Tamagui PoC)', () => {
  it('renders children content as a real button element', () => {
    renderButton(<ButtonTamagui>Click me</ButtonTamagui>);
    const button = screen.getByRole('button');
    expect(button).toHaveTextContent('Click me');
    expect(button.tagName).toBe('BUTTON');
  });

  it('applies primary variant background by default', () => {
    renderButton(<ButtonTamagui>Primary</ButtonTamagui>);
    const button = screen.getByRole('button');
    expect(getComputedStyle(button).backgroundColor).toBe('#007a32');
  });

  it('applies secondary variant background', () => {
    renderButton(<ButtonTamagui variant="secondary">Secondary</ButtonTamagui>);
    const button = screen.getByRole('button');
    expect(getComputedStyle(button).backgroundColor).toBe('#e7fff1');
  });

  it('applies danger variant background', () => {
    renderButton(<ButtonTamagui variant="danger">Danger</ButtonTamagui>);
    const button = screen.getByRole('button');
    expect(getComputedStyle(button).backgroundColor).toBe('#c62828');
  });

  it('fires onClick', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    renderButton(<ButtonTamagui onClick={onClick}>Click</ButtonTamagui>);

    await user.click(screen.getByRole('button'));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  // PoC finding (issue #629): a real a11y parity gap, not a test-writing
  // slip - Tamagui's Button sets `aria-disabled="true"` on `disabled` but
  // does not set the native HTML `disabled` attribute the way the original
  // (a plain <button disabled>) does, so the element stays focusable/
  // clickable via assistive tech and keyboard unless every consumer also
  // guards `onPress`. `it.fails` records this as a known, verified gap
  // rather than silently passing or leaving a red test in the suite.
  it.fails('disables the button', () => {
    renderButton(<ButtonTamagui disabled>Disabled</ButtonTamagui>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
