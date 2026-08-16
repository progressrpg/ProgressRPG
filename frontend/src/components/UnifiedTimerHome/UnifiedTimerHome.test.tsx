import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import UnifiedTimerHome from './UnifiedTimerHome';

const mockUseGame = vi.fn();
const mockUseSupportFlow = vi.fn();
const mockUseEntitySearchCache = vi.fn();
const mockUseDefaultActivityEntries = vi.fn();
const mockUseFeatureFlag = vi.fn();
const fetchPlayerAndCharacter = vi.fn();
const fetchCharacterCurrent = vi.fn();
const fetchActivities = vi.fn();
const clearAutoStopCompletion = vi.fn();
const stop = vi.fn();
const startActivity = vi.fn();
const labelActivity = vi.fn();
const addEntityToCache = vi.fn();

const mockUseTasks = vi.fn();
const mockUseCreateTask = vi.fn();
const mockUseUpdateTask = vi.fn();
const mockUseDeleteTask = vi.fn();
const mockUseNotes = vi.fn();
const mockUseCreateNote = vi.fn();
const navigate = vi.fn();

vi.mock('../../hooks/useGame', () => ({
  useGame: () => mockUseGame(),
}));

vi.mock('../../hooks/useTasks', () => ({
  useTasks: () => mockUseTasks(),
  useCreateTask: () => mockUseCreateTask(),
  useUpdateTask: () => mockUseUpdateTask(),
  useDeleteTask: () => mockUseDeleteTask(),
}));

vi.mock('../../hooks/useNotes', () => ({
  useNotes: (...args: unknown[]) => mockUseNotes(...args),
  useCreateNote: () => mockUseCreateNote(),
}));

vi.mock('react-router', () => ({
  useNavigate: () => navigate,
}));

vi.mock('../../hooks/useSupportFlow', () => ({
  useSupportFlow: (...args: unknown[]) => mockUseSupportFlow(...args),
}));

vi.mock('../../hooks/useEntitySearchCache', () => ({
  useEntitySearchCache: (...args: unknown[]) => mockUseEntitySearchCache(...args),
}));

vi.mock('../../hooks/useFeatureFlag', () => ({
  useFeatureFlag: (flag: string) => mockUseFeatureFlag(flag),
}));

vi.mock('../../hooks/useDefaultActivityEntries', () => ({
  useDefaultActivityEntries: () => mockUseDefaultActivityEntries(),
}));

vi.mock('../../hooks/useActivities', () => ({
  useUpdateActivity: () => ({ mutate: vi.fn() }),
}));

vi.mock('../SupportFlow/SupportFlowModal', () => ({
  default: () => null,
}));

vi.mock('./TimerNoteField', () => ({
  default: ({ taskId, activityId }: { taskId: number | null; activityId: number | null }) => (
    <div data-testid="timer-note-field" data-task-id={taskId ?? ''} data-activity-id={activityId ?? ''} />
  ),
}));

vi.mock('../../utils/sounds', () => ({
  playLimitReachedSound: vi.fn(),
  primeAudio: vi.fn(),
}));

// Strip animation-only props so React doesn't warn about unknown DOM attrs,
// and render children synchronously so tests don't need to await exit/enter
// transitions.
function stripMotionProps(props: Record<string, unknown>) {
  const { layout, initial, animate, exit, transition, children, ...rest } = props;
  void layout;
  void initial;
  void animate;
  void exit;
  void transition;
  return { rest, children: children as React.ReactNode };
}

vi.mock('framer-motion', () => ({
  motion: {
    div: React.forwardRef<HTMLDivElement, Record<string, unknown>>((props, ref) => {
      const { rest, children } = stripMotionProps(props);
      return (
        <div ref={ref} {...rest}>
          {children}
        </div>
      );
    }),
    button: React.forwardRef<HTMLButtonElement, Record<string, unknown>>((props, ref) => {
      const { rest, children } = stripMotionProps(props);
      return (
        <button ref={ref} {...rest}>
          {children}
        </button>
      );
    }),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  };
});

function mockGame(activityTimerOverrides: Record<string, unknown> = {}) {
  mockUseGame.mockReturnValue({
    activityTimer: {
      currentActivity: null,
      status: 'empty',
      stop,
      startActivity,
      labelActivity,
      elapsed: 0,
      limitSeconds: null,
      limitReached: false,
      autoStopCompletion: null,
      clearAutoStopCompletion,
      ...activityTimerOverrides,
    },
    fetchPlayerAndCharacter,
    fetchCharacterCurrent,
    fetchActivities,
    loginState: 'none',
    loginStreak: 0,
    loginEventAt: null,
    player: { is_premium: false },
    freeTimerLimitSeconds: 15,
  });
}

describe('UnifiedTimerHome', () => {
  beforeEach(() => {
    mockUseSupportFlow.mockReset();
    mockUseEntitySearchCache.mockReset();
    mockUseDefaultActivityEntries.mockReset().mockReturnValue([]);
    mockUseFeatureFlag.mockReset().mockReturnValue(false);
    fetchPlayerAndCharacter.mockReset().mockResolvedValue(null);
    fetchCharacterCurrent.mockReset().mockResolvedValue(null);
    fetchActivities.mockReset().mockResolvedValue(null);
    clearAutoStopCompletion.mockReset();
    stop.mockReset();
    startActivity.mockReset();
    labelActivity.mockReset();
    addEntityToCache.mockReset();
    navigate.mockReset();

    mockUseTasks.mockReset().mockReturnValue({ isLoading: false, data: [] });
    mockUseCreateTask.mockReset().mockReturnValue({ mutate: vi.fn() });
    mockUseUpdateTask.mockReset().mockReturnValue({ mutate: vi.fn() });
    mockUseDeleteTask.mockReset().mockReturnValue({ mutate: vi.fn() });
    mockUseNotes.mockReset().mockReturnValue({ isLoading: false, data: [] });
    mockUseCreateNote.mockReset().mockReturnValue({ mutate: vi.fn() });

    mockUseSupportFlow.mockReturnValue({
      openWelcomeMessage: vi.fn(),
      openActivityReward: vi.fn(),
      openSupportMode: vi.fn(),
      flowState: { isOpen: false },
      flowDispatch: vi.fn(),
      handleConfirmActivity: vi.fn(),
    });

    mockUseEntitySearchCache.mockReturnValue({
      entities: [],
      addEntityToCache,
    });

    mockGame();
  });

  it('renders the input state by default with a single, always-enabled Start button', () => {
    render(<UnifiedTimerHome />);

    expect(screen.getByRole('combobox', { name: 'Activity name' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Start blank' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start' })).toBeEnabled();
  });

  it('Start with an empty input labels the timer "Planning" and switches to Planning mode', async () => {
    const user = userEvent.setup();
    startActivity.mockResolvedValue(null);

    const { rerender } = render(<UnifiedTimerHome />);

    await user.click(screen.getByRole('button', { name: 'Start' }));

    expect(startActivity).toHaveBeenCalledWith({ text: 'Planning', limitSeconds: 15 });

    // Reflect the timer now being active, labelled "Planning".
    mockGame({ status: 'active', currentActivity: { name: 'Planning' } });
    rerender(<UnifiedTimerHome />);

    expect(screen.getByRole('button', { name: /Planning/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Planning' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByPlaceholderText('New task name')).toBeInTheDocument();
  });

  it('Start/Stop is the same persistent button element, not a swap', async () => {
    const user = userEvent.setup();
    startActivity.mockResolvedValue(null);

    const { rerender } = render(<UnifiedTimerHome />);
    const startButton = screen.getByRole('button', { name: 'Start' });

    await user.click(startButton);
    mockGame({ status: 'active', currentActivity: { name: 'Planning' } });
    rerender(<UnifiedTimerHome />);

    expect(screen.getByRole('button', { name: 'Stop' })).toBe(startButton);
  });

  it('Start with typed text starts a named timer instead of a blank one', async () => {
    const user = userEvent.setup();
    startActivity.mockResolvedValue(null);

    render(<UnifiedTimerHome />);

    await user.type(screen.getByRole('combobox', { name: 'Activity name' }), 'Deep work');
    await user.click(screen.getByRole('button', { name: 'Start' }));

    expect(startActivity).toHaveBeenCalledWith({ text: 'Deep work', limitSeconds: 15 });
  });

  it('selecting a suggestion while unlabelled-running labels the timer in place', async () => {
    const user = userEvent.setup();
    mockGame({ status: 'active', currentActivity: { name: '' } });
    mockUseDefaultActivityEntries.mockReturnValue([
      { id: 'activity-1', name: 'Washing dishes', taskId: null, source: 'activity' },
    ]);

    render(<UnifiedTimerHome />);

    await user.click(screen.getByRole('option', { name: 'Washing dishes' }));

    expect(labelActivity).toHaveBeenCalledWith('Washing dishes', null);
    expect(startActivity).not.toHaveBeenCalled();
  });

  it('shows the running-labelled state with a clickable activity name', () => {
    mockGame({ status: 'active', currentActivity: { name: 'Deep work' }, elapsed: 15 });

    render(<UnifiedTimerHome />);

    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Deep work/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument();
  });

  it('clicking the running-labelled name switches to click-to-edit and pre-fills the input', async () => {
    const user = userEvent.setup();
    mockGame({ status: 'active', currentActivity: { name: 'Deep work' } });

    render(<UnifiedTimerHome />);

    await user.click(screen.getByRole('button', { name: /Deep work/ }));

    expect(screen.getByRole('combobox', { name: 'Activity name' })).toHaveValue('Deep work');
    expect(screen.getByRole('combobox', { name: 'Activity name' })).toHaveFocus();
  });

  it('Escape cancels click-to-edit without calling labelActivity', async () => {
    const user = userEvent.setup();
    mockGame({ status: 'active', currentActivity: { name: 'Deep work' } });

    render(<UnifiedTimerHome />);

    await user.click(screen.getByRole('button', { name: /Deep work/ }));
    await user.keyboard('{Escape}');

    expect(labelActivity).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /Deep work/ })).toBeInTheDocument();
  });

  it('exposes a status message for screen readers reflecting the running state', () => {
    mockGame({ status: 'active', currentActivity: { name: 'Deep work' } });

    render(<UnifiedTimerHome />);

    expect(screen.getByText('Timer running: Deep work')).toBeInTheDocument();
  });

  it('shows the auto-stop warning near the limit', () => {
    mockGame({
      status: 'active',
      currentActivity: { name: 'Deep work' },
      elapsed: 27,
      limitSeconds: 30,
    });

    render(<UnifiedTimerHome />);

    expect(
      screen.getByText('This timer will stop automatically when it reaches 0:30.')
    ).toBeInTheDocument();
  });

  it('renders the Results panel instead of the timer body after a results_mode stop', async () => {
    const user = userEvent.setup();
    mockUseFeatureFlag.mockImplementation((flag: string) => flag === 'results_mode');
    mockGame({ status: 'active', currentActivity: { id: 1, name: 'Deep work' }, elapsed: 30 });
    stop.mockResolvedValue({
      xp_gained: 10,
      base_xp: 10,
      xp_multiplier: 1,
      level_ups: [],
      duration_seconds: 30,
    });

    render(<UnifiedTimerHome />);

    await user.click(screen.getByRole('button', { name: 'Stop' }));

    expect(
      screen.getByText('Nice work ⚔️ You spent 30 seconds on "Deep work".')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back to timer' })).toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: 'Activity name' })).not.toBeInTheDocument();
  });

  describe('mode switching', () => {
    it('hides the mode switcher and tasks panel while the timer is idle', () => {
      render(<UnifiedTimerHome />);

      expect(screen.queryByRole('radiogroup', { name: 'Timer view' })).not.toBeInTheDocument();
      expect(screen.queryByPlaceholderText('New task name')).not.toBeInTheDocument();
    });

    it('shows the mode switcher, defaulted to Doing, once the timer is running', () => {
      mockGame({ status: 'active', currentActivity: { name: '' } });
      render(<UnifiedTimerHome />);

      expect(screen.getByRole('radio', { name: 'Doing' })).toHaveAttribute('aria-checked', 'true');
      expect(screen.queryByPlaceholderText('New task name')).not.toBeInTheDocument();
    });

    it('auto-selects Planning when the activity name contains "plan"', async () => {
      const user = userEvent.setup();
      mockGame({ status: 'active', currentActivity: { name: '' } });
      render(<UnifiedTimerHome />);

      await user.type(screen.getByRole('combobox', { name: 'Activity name' }), 'Plan my week');

      expect(screen.getByRole('radio', { name: 'Planning' })).toHaveAttribute('aria-checked', 'true');
      expect(screen.getByPlaceholderText('New task name')).toBeInTheDocument();
    });

    it('matches "plan" case-insensitively and as a substring (e.g. "Planning")', async () => {
      const user = userEvent.setup();
      mockGame({ status: 'active', currentActivity: { name: '' } });
      render(<UnifiedTimerHome />);

      await user.type(screen.getByRole('combobox', { name: 'Activity name' }), 'PLANNING session');

      expect(screen.getByRole('radio', { name: 'Planning' })).toHaveAttribute('aria-checked', 'true');
    });

    it('does not auto-select Planning for names without "plan"', async () => {
      const user = userEvent.setup();
      mockGame({ status: 'active', currentActivity: { name: '' } });
      render(<UnifiedTimerHome />);

      await user.type(screen.getByRole('combobox', { name: 'Activity name' }), 'Deep work');

      expect(screen.getByRole('radio', { name: 'Doing' })).toHaveAttribute('aria-checked', 'true');
    });

    it('clicking the Planning chip renders TasksPanel and keeps timer controls visible', async () => {
      const user = userEvent.setup();
      mockGame({ status: 'active', currentActivity: { name: '' } });
      render(<UnifiedTimerHome />);

      await user.click(screen.getByRole('radio', { name: 'Planning' }));

      expect(screen.getByRole('radio', { name: 'Planning' })).toHaveAttribute('aria-checked', 'true');
      expect(screen.getByPlaceholderText('New task name')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument();
    });

    it('switching back to Doing unmounts TasksPanel', async () => {
      const user = userEvent.setup();
      mockGame({ status: 'active', currentActivity: { name: '' } });
      render(<UnifiedTimerHome />);

      await user.click(screen.getByRole('radio', { name: 'Planning' }));
      expect(screen.getByPlaceholderText('New task name')).toBeInTheDocument();

      await user.click(screen.getByRole('radio', { name: 'Doing' }));
      expect(screen.queryByPlaceholderText('New task name')).not.toBeInTheDocument();
    });

    it('timer controls stay functional while in Planning mode', async () => {
      const user = userEvent.setup();
      mockGame({ status: 'active', currentActivity: { name: '' } });
      render(<UnifiedTimerHome />);

      await user.click(screen.getByRole('radio', { name: 'Planning' }));
      expect(screen.getByPlaceholderText('New task name')).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: 'Stop' }));
      expect(stop).toHaveBeenCalled();
    });

    it('switching mode does not itself reset an in-progress label edit beyond the blur it naturally causes', async () => {
      // Clicking the Planning chip blurs the focused edit input, which
      // `handleWrapperBlur` already commits (same as clicking anywhere else
      // outside the card) — the mode switch itself doesn't add any extra
      // reset logic on top of that pre-existing behaviour.
      const user = userEvent.setup();
      mockGame({ status: 'active', currentActivity: { name: 'Deep work' } });
      render(<UnifiedTimerHome />);

      await user.click(screen.getByRole('button', { name: /Deep work/ }));
      expect(screen.getByRole('combobox', { name: 'Activity name' })).toHaveValue('Deep work');

      await user.click(screen.getByRole('radio', { name: 'Planning' }));
      await user.click(screen.getByRole('radio', { name: 'Doing' }));

      expect(screen.getByRole('button', { name: /Deep work/ })).toBeInTheDocument();
      expect(labelActivity).toHaveBeenCalledWith('Deep work', null);
    });
  });

  describe('timer note field', () => {
    it('is hidden while the notesFeature flag is off, even with an active labelled timer', () => {
      mockUseFeatureFlag.mockReset().mockReturnValue(false);
      mockGame({ status: 'active', currentActivity: { name: 'Deep work', taskId: 5 } });
      render(<UnifiedTimerHome />);

      expect(screen.queryByTestId('timer-note-field')).not.toBeInTheDocument();
    });

    it('is shown in Doing mode once notesFeature is on and the timer has a task', () => {
      mockUseFeatureFlag.mockReset().mockImplementation((flag: string) => flag === 'notesFeature');
      mockGame({ status: 'active', currentActivity: { name: 'Deep work', taskId: 5 } });
      render(<UnifiedTimerHome />);

      const field = screen.getByTestId('timer-note-field');
      expect(field).toHaveAttribute('data-task-id', '5');
    });

    it('is shown once notesFeature is on and the timer has a catalog activity but no task', () => {
      mockUseFeatureFlag.mockReset().mockImplementation((flag: string) => flag === 'notesFeature');
      mockGame({ status: 'active', currentActivity: { name: 'Washing dishes', activity: 7 } });
      render(<UnifiedTimerHome />);

      const field = screen.getByTestId('timer-note-field');
      expect(field).toHaveAttribute('data-activity-id', '7');
    });

    it('stays hidden for a still-nameless running timer, even with the flag on', () => {
      mockUseFeatureFlag.mockReset().mockImplementation((flag: string) => flag === 'notesFeature');
      mockGame({ status: 'active', currentActivity: { name: '' } });
      render(<UnifiedTimerHome />);

      expect(screen.queryByTestId('timer-note-field')).not.toBeInTheDocument();
    });

    it('is hidden in Planning mode even with the flag on and a task attached', async () => {
      const user = userEvent.setup();
      mockUseFeatureFlag.mockReset().mockImplementation((flag: string) => flag === 'notesFeature');
      mockGame({ status: 'active', currentActivity: { name: 'Deep work', taskId: 5 } });
      render(<UnifiedTimerHome />);

      await user.click(screen.getByRole('radio', { name: 'Planning' }));

      expect(screen.queryByTestId('timer-note-field')).not.toBeInTheDocument();
    });
  });
});
