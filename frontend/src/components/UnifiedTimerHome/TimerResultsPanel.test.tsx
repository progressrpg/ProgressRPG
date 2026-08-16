import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import TimerResultsPanel from './TimerResultsPanel';
import type { ResultsData } from '../ActivityInput/useActivityInput';

const mockUseGame = vi.fn();
const mockUseTasks = vi.fn();
const updateTaskMutate = vi.fn();
const updateActivityMutate = vi.fn();
const mockUseEntitySearchCache = vi.fn();
const addEntityToCache = vi.fn();

vi.mock('../../hooks/useGame', () => ({
  useGame: () => mockUseGame(),
}));

vi.mock('../../hooks/useTasks', () => ({
  useTasks: () => mockUseTasks(),
  useUpdateTask: () => ({ mutate: updateTaskMutate, data: undefined }),
}));

vi.mock('../../hooks/useActivities', () => ({
  useUpdateActivity: () => ({ mutate: updateActivityMutate }),
}));

vi.mock('../../hooks/useEntitySearchCache', () => ({
  useEntitySearchCache: () => mockUseEntitySearchCache(),
}));

function baseResults(overrides: Partial<ResultsData> = {}): ResultsData {
  return {
    activityId: 5,
    activityName: 'Write tests',
    xpGained: 27,
    baseXp: 27,
    xpMultiplier: 1,
    taskXpMultiplier: null,
    levelUps: [],
    isAutoStopped: false,
    showUpgradePrompt: false,
    elapsedSeconds: 90,
    taskId: null,
    ...overrides,
  };
}

describe('TimerResultsPanel', () => {
  beforeEach(() => {
    mockUseGame.mockReset().mockReturnValue({ fetchPlayerAndCharacter: vi.fn() });
    mockUseTasks.mockReset().mockReturnValue({ data: [] });
    updateTaskMutate.mockReset();
    updateActivityMutate.mockReset();
    mockUseEntitySearchCache.mockReset().mockReturnValue({ entities: [], addEntityToCache });
  });

  it('shows the reward breakdown and a manual-only exit, with no auto-continue countdown', () => {
    const onExit = vi.fn();
    render(<TimerResultsPanel results={baseResults()} onExit={onExit} />);

    expect(
      screen.getByText('Nice work ⚔️ You spent 1 minute 30 seconds on "Write tests".')
    ).toBeInTheDocument();
    expect(screen.queryByText(/Continue with support/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Back to timer' }));
    expect(onExit).toHaveBeenCalledTimes(1);
  });

  it('shows the task summary and complete/undo toggle when task-linked', () => {
    mockUseTasks.mockReturnValue({
      data: [{ id: 9, name: 'Ship it', is_complete: false, total_time: 120 }],
    });

    render(<TimerResultsPanel results={baseResults({ taskId: 9 })} onExit={vi.fn()} />);

    expect(screen.getByText('Task: Ship it')).toBeInTheDocument();
    const checkbox = screen.getByLabelText('Completed task?');
    fireEvent.click(checkbox);

    expect(updateTaskMutate).toHaveBeenCalledWith(
      { id: 9, data: { is_complete: true } },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    );
  });

  it('shows an inline labeling entry point for an unlabelled activity', () => {
    render(
      <TimerResultsPanel
        results={baseResults({ activityName: null, taskId: null })}
        onExit={vi.fn()}
      />
    );

    expect(screen.getByText('Nice work ⚔️ You spent 1 minute 30 seconds focused.')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Label this activity' })).toBeInTheDocument();
  });

  it('debounces the live relabel and commits ~1s after the last keystroke', () => {
    vi.useFakeTimers();

    render(
      <TimerResultsPanel
        results={baseResults({ activityId: 42, activityName: null, taskId: null })}
        onExit={vi.fn()}
      />
    );

    const input = screen.getByRole('combobox', { name: 'Label this activity' });
    fireEvent.change(input, { target: { value: 'Washing dishes' } });

    expect(updateActivityMutate).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(updateActivityMutate).toHaveBeenCalledWith({
      activityId: 42,
      data: { name: 'Washing dishes', task_id: null },
    });

    vi.useRealTimers();
  });

  it('shows the upgrade prompt when flagged and not already premium-level', () => {
    render(
      <TimerResultsPanel
        results={baseResults({ showUpgradePrompt: true, isAutoStopped: true })}
        onExit={vi.fn()}
      />
    );

    expect(
      screen.getByText('Need more time? Upgrade to Premium for unlimited timer sessions.')
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Upgrade to Premium' })).toHaveAttribute('href', '/upgrade');
  });

  it('does not show the upgrade prompt for likely-premium multipliers', () => {
    render(
      <TimerResultsPanel
        results={baseResults({ showUpgradePrompt: true, xpMultiplier: 2 })}
        onExit={vi.fn()}
      />
    );

    expect(screen.queryByText(/Upgrade to Premium/)).not.toBeInTheDocument();
  });
});
