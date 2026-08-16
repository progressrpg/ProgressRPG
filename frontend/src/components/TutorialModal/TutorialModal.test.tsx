import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render as rtlRender, screen, fireEvent, waitFor } from '@testing-library/react';
import { TamaguiProvider } from 'tamagui';
import TutorialModal from './TutorialModal';
import tamaguiConfig from '../../../tamagui.config';

// TutorialModal renders Modal (#582), which needs a TamaguiProvider
// ancestor - unlike Radix's Dialog.Root, it isn't usable standalone. The
// app root (src/main.tsx) provides this in production; tests need their own.
function render(...args: Parameters<typeof rtlRender>) {
  const [ui, options] = args;
  return rtlRender(ui, {
    wrapper: ({ children }) => (
      <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
        {children}
      </TamaguiProvider>
    ),
    ...options,
  });
}

const mockUseTutorialSteps = vi.fn();
const mockApiFetch = vi.fn();

vi.mock('../../hooks/useTutorialSteps', () => ({
  default: () => mockUseTutorialSteps(),
}));

vi.mock('../../utils/api', () => ({
  apiFetch: (...args) => mockApiFetch(...args),
}));

const STEPS = [
  { id: 1, title: 'Welcome', body: 'Get started here', image_url: null, alt_text: '', youtube_url: '' },
  { id: 2, title: 'Track Tasks', body: 'Log your tasks', image_url: 'https://example.com/screenshot.png', alt_text: 'Task screen', youtube_url: '' },
  { id: 3, title: 'Earn XP', body: 'Level up your character', image_url: null, alt_text: '', youtube_url: 'https://www.youtube.com/watch?v=abc123' },
];

describe('TutorialModal', () => {
  const onClose = vi.fn();
  const onComplete = vi.fn();

  beforeEach(() => {
    vi.resetAllMocks();
    mockUseTutorialSteps.mockReturnValue({ steps: STEPS, isLoading: false });
    mockApiFetch.mockResolvedValue({});
  });

  // --- Loading / empty states ---

  it('renders nothing while loading', () => {
    mockUseTutorialSteps.mockReturnValue({ steps: [], isLoading: true });
    render(<TutorialModal onClose={onClose} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows an empty-state message when there are no steps', () => {
    mockUseTutorialSteps.mockReturnValue({ steps: [], isLoading: false });
    render(<TutorialModal onClose={onClose} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('No tutorial content to display yet.')).toBeInTheDocument();
  });

  it('allows closing the modal in the empty state', () => {
    mockUseTutorialSteps.mockReturnValue({ steps: [], isLoading: false });
    render(<TutorialModal onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: 'Close modal' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // --- Basic rendering ---

  it('shows the first step title and body', () => {
    render(<TutorialModal onClose={onClose} />);
    expect(screen.getByRole('heading', { name: 'Welcome' })).toBeInTheDocument();
    expect(screen.getByText('Get started here')).toBeInTheDocument();
  });

  it('shows the step count', () => {
    render(<TutorialModal onClose={onClose} />);
    expect(screen.getByText('1 / 3')).toBeInTheDocument();
  });

  it('step count has aria-live and aria-atomic for screen readers', () => {
    render(<TutorialModal onClose={onClose} />);
    const counter = screen.getByText('1 / 3');
    expect(counter).toHaveAttribute('aria-live', 'polite');
    expect(counter).toHaveAttribute('aria-atomic', 'true');
  });

  // --- Navigation visibility ---

  it('hides the Previous button on the first step', () => {
    render(<TutorialModal onClose={onClose} />);
    // inert removes the button from the a11y tree, so use querySelector
    const prevWrapper = document.body.querySelector('button[aria-label="Previous step"]')!.parentElement;
    expect(prevWrapper).toHaveAttribute('inert');
  });

  it('shows the Next button on the first step', () => {
    render(<TutorialModal onClose={onClose} />);
    const nextWrapper = document.body.querySelector('button[aria-label="Next step"]')!.parentElement;
    expect(nextWrapper).not.toHaveAttribute('inert');
  });

  it('hides the Next button on the last step', () => {
    mockUseTutorialSteps.mockReturnValue({
      steps: [STEPS[0]],
      isLoading: false,
    });
    render(<TutorialModal onClose={onClose} />);
    const nextWrapper = document.body.querySelector('button[aria-label="Next step"]')!.parentElement;
    expect(nextWrapper).toHaveAttribute('inert');
  });

  it('shows both nav buttons on middle steps', () => {
    render(<TutorialModal onClose={onClose} />);
    fireEvent.click(document.body.querySelector('button[aria-label="Next step"]')!);
    expect(document.body.querySelector('button[aria-label="Previous step"]')!.parentElement).not.toHaveAttribute('inert');
    expect(document.body.querySelector('button[aria-label="Next step"]')!.parentElement).not.toHaveAttribute('inert');
  });

  // --- Navigation behaviour ---

  it('advances to the next step', () => {
    render(<TutorialModal onClose={onClose} />);
    fireEvent.click(document.body.querySelector('button[aria-label="Next step"]')!);
    expect(screen.getByRole('heading', { name: 'Track Tasks' })).toBeInTheDocument();
    expect(screen.getByText('2 / 3')).toBeInTheDocument();
  });

  it('goes back to the previous step', () => {
    render(<TutorialModal onClose={onClose} />);
    fireEvent.click(document.body.querySelector('button[aria-label="Next step"]')!);
    fireEvent.click(document.body.querySelector('button[aria-label="Previous step"]')!);
    expect(screen.getByRole('heading', { name: 'Welcome' })).toBeInTheDocument();
    expect(screen.getByText('1 / 3')).toBeInTheDocument();
  });

  // --- startAtStepId ---

  it('starts at the given step when startAtStepId matches', () => {
    render(<TutorialModal onClose={onClose} startAtStepId={2} />);
    expect(screen.getByRole('heading', { name: 'Track Tasks' })).toBeInTheDocument();
    expect(screen.getByText('2 / 3')).toBeInTheDocument();
  });

  it('falls back to the first step when startAtStepId is not found', () => {
    render(<TutorialModal onClose={onClose} startAtStepId={999} />);
    expect(screen.getByRole('heading', { name: 'Welcome' })).toBeInTheDocument();
  });

  // --- Media ---

  it('shows an image when image_url is present', () => {
    render(<TutorialModal onClose={onClose} startAtStepId={2} />);
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', 'https://example.com/screenshot.png');
    expect(img).toHaveAttribute('alt', 'Task screen');
  });

  it('uses the step title as alt text when alt_text is empty', () => {
    mockUseTutorialSteps.mockReturnValue({
      steps: [{ id: 1, title: 'Welcome', body: '', image_url: 'https://example.com/img.png', alt_text: '', youtube_url: '' }],
      isLoading: false,
    });
    render(<TutorialModal onClose={onClose} />);
    expect(screen.getByRole('img')).toHaveAttribute('alt', 'Welcome');
  });

  it('does not show an image when image_url is absent', () => {
    render(<TutorialModal onClose={onClose} />);
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('embeds a YouTube video for a youtube.com URL', () => {
    render(<TutorialModal onClose={onClose} startAtStepId={3} />);
    const iframe = screen.getByTitle('Earn XP');
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute('src', 'https://www.youtube-nocookie.com/embed/abc123');
  });

  it('embeds a YouTube video for a youtu.be URL', () => {
    mockUseTutorialSteps.mockReturnValue({
      steps: [{ id: 1, title: 'Short link', body: '', image_url: null, alt_text: '', youtube_url: 'https://youtu.be/xyz789' }],
      isLoading: false,
    });
    render(<TutorialModal onClose={onClose} />);
    expect(screen.getByTitle('Short link')).toHaveAttribute('src', 'https://www.youtube-nocookie.com/embed/xyz789');
  });

  it('does not render an iframe when youtube_url is empty', () => {
    render(<TutorialModal onClose={onClose} />);
    expect(screen.queryByTitle('Welcome')).not.toBeInTheDocument();
  });

  // --- Done / close ---

  it('calls onClose when the close button is clicked', () => {
    render(<TutorialModal onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: 'Close modal' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('Done marks remaining steps as seen, calls onComplete then onClose', async () => {
    render(<TutorialModal onClose={onClose} onComplete={onComplete} startAtStepId={2} />);
    fireEvent.click(screen.getByRole('button', { name: '✓ Done' }));

    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));

    expect(mockApiFetch).toHaveBeenCalledWith(
      '/me/mark_tutorial_steps_seen/',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ step_ids: [2, 3] }),
      }),
    );
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('Done still closes the modal if the API call fails', async () => {
    mockApiFetch.mockRejectedValue(new Error('Network error'));
    render(<TutorialModal onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: '✓ Done' }));

    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });
});
