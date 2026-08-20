import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';
import FeedbackWidget from './FeedbackWidget';
import tamaguiConfig from '../../../tamagui.config';

// The underlying Tamagui Popover (#585) needs a TamaguiProvider ancestor,
// same as Tooltip (#583) and AlertDialog (#582) - the app root (src/main.tsx)
// provides this in production; tests need their own.
function renderWidget() {
  return render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      <FeedbackWidget />
    </TamaguiProvider>
  );
}

describe('FeedbackWidget', () => {
  it('does not show the feedback panel until the button is clicked', () => {
    renderWidget();
    expect(screen.queryByText('Help us improve Progress RPG')).not.toBeInTheDocument();
  });

  it('opens the feedback panel with both survey links on click', async () => {
    const user = userEvent.setup();
    renderWidget();

    await user.click(screen.getByRole('button', { name: '💬 Feedback' }));

    expect(await screen.findByText('Help us improve Progress RPG')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Quick feedback/ })).toHaveAttribute(
      'href',
      'https://forms.gle/uCCg2grwzgVwwB617'
    );
    expect(screen.getByRole('link', { name: /First impressions/ })).toHaveAttribute(
      'href',
      'https://forms.gle/bHPqtd7ukbwF4WGu8'
    );
  });

  it('closes the panel via the close button', async () => {
    const user = userEvent.setup();
    renderWidget();

    await user.click(screen.getByRole('button', { name: '💬 Feedback' }));
    await screen.findByText('Help us improve Progress RPG');

    await user.click(screen.getByRole('button', { name: 'Close feedback panel' }));

    await waitFor(() => {
      expect(screen.queryByText('Help us improve Progress RPG')).not.toBeInTheDocument();
    });
  });
});
