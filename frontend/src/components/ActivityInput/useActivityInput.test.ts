import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useActivityInput } from './useActivityInput';

const mockUseGame = vi.fn();
const mockUseSupportFlow = vi.fn();
const mockUseEntitySearchCache = vi.fn();
const fetchPlayerAndCharacter = vi.fn();
const fetchCharacterCurrent = vi.fn();
const fetchActivities = vi.fn();
const clearAutoStopCompletion = vi.fn();
const stop = vi.fn();
const startActivity = vi.fn();
const labelActivity = vi.fn();
const addEntityToCache = vi.fn();

vi.mock('../../hooks/useGame', () => ({
  useGame: () => mockUseGame(),
}));

vi.mock('../../hooks/useSupportFlow', () => ({
  useSupportFlow: (...args: unknown[]) => mockUseSupportFlow(...args),
}));

vi.mock('../../hooks/useEntitySearchCache', () => ({
  useEntitySearchCache: (...args: unknown[]) => mockUseEntitySearchCache(...args),
}));

vi.mock('../../utils/sounds', () => ({
  playLimitReachedSound: vi.fn(),
  primeAudio: vi.fn(),
}));

const invalidateQueries = vi.fn();

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries }),
  };
});

function mockGame(activityTimerOverrides: Record<string, unknown> = {}, gameOverrides: Record<string, unknown> = {}) {
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
    ...gameOverrides,
  });
}

describe('useActivityInput unified handlers', () => {
  beforeEach(() => {
    mockUseSupportFlow.mockReset();
    mockUseEntitySearchCache.mockReset();
    fetchPlayerAndCharacter.mockReset().mockResolvedValue(null);
    fetchCharacterCurrent.mockReset().mockResolvedValue(null);
    fetchActivities.mockReset().mockResolvedValue(null);
    clearAutoStopCompletion.mockReset();
    stop.mockReset();
    startActivity.mockReset();
    labelActivity.mockReset();
    addEntityToCache.mockReset();
    invalidateQueries.mockReset();

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

  it('handleBlankStart starts a timer with allowBlank and no text', async () => {
    const { result } = renderHook(() => useActivityInput());

    await act(async () => {
      await result.current.handleBlankStart();
    });

    expect(startActivity).toHaveBeenCalledWith({
      text: '',
      allowBlank: true,
      limitSeconds: 15,
    });
  });

  it('isUnlabelled is true when active with a blank current activity name', () => {
    mockGame({ status: 'active', currentActivity: { name: '' } });

    const { result } = renderHook(() => useActivityInput());

    expect(result.current.isUnlabelled).toBe(true);
  });

  it('isUnlabelled is false when active with a real current activity name', () => {
    mockGame({ status: 'active', currentActivity: { name: 'Write docs' } });

    const { result } = renderHook(() => useActivityInput());

    expect(result.current.isUnlabelled).toBe(false);
  });

  it('handleUnifiedSelect starts a new timer when nothing is running', async () => {
    const { result } = renderHook(() => useActivityInput());

    await act(async () => {
      await result.current.handleUnifiedSelect({ name: 'Washing dishes', id: 1, source: 'activity' });
    });

    expect(startActivity).toHaveBeenCalledWith(
      expect.objectContaining({ text: 'Washing dishes', limitSeconds: 15 })
    );
    expect(labelActivity).not.toHaveBeenCalled();
  });

  it('handleUnifiedSelect labels the running timer instead of starting a new one', async () => {
    mockGame({ status: 'active', currentActivity: { name: '' } });

    const { result } = renderHook(() => useActivityInput());

    await act(async () => {
      await result.current.handleUnifiedSelect({ name: 'Deep work', id: 1, source: 'activity' });
    });

    expect(labelActivity).toHaveBeenCalledWith('Deep work', null);
    expect(startActivity).not.toHaveBeenCalled();
  });

  it('handleUnifiedSelect resolves a task-linked selection into a taskId when relabelling', async () => {
    mockGame({ status: 'active', currentActivity: { name: '' } });

    const { result } = renderHook(() => useActivityInput());

    await act(async () => {
      await result.current.handleUnifiedSelect({ name: 'Ship it', id: 7, source: 'task' });
    });

    expect(labelActivity).toHaveBeenCalledWith('Ship it', 7);
  });

  it('handleUnifiedSubmit is a no-op for blank text when nothing is running', async () => {
    const { result } = renderHook(() => useActivityInput());

    await act(async () => {
      await result.current.handleUnifiedSubmit('   ');
    });

    expect(startActivity).not.toHaveBeenCalled();
    expect(labelActivity).not.toHaveBeenCalled();
  });

  it('handleUnifiedSubmit relabels the running timer even with blank text (clears the label)', async () => {
    mockGame({ status: 'active', currentActivity: { name: 'Old label' } });

    const { result } = renderHook(() => useActivityInput());

    await act(async () => {
      await result.current.handleUnifiedSubmit('   ');
    });

    expect(labelActivity).toHaveBeenCalledWith('', null);
    expect(startActivity).not.toHaveBeenCalled();
  });

  it('startEditingLabel pre-fills the input with the current activity name', () => {
    mockGame({ status: 'active', currentActivity: { name: 'Deep work' } });

    const { result } = renderHook(() => useActivityInput());

    act(() => {
      result.current.startEditingLabel();
    });

    expect(result.current.name).toBe('Deep work');
    expect(result.current.isEditingLabel).toBe(true);
  });

  it('inputValue reflects a fully-cleared name while editing, instead of falling back to the old committed name', () => {
    mockGame({ status: 'active', currentActivity: { name: 'Deep work' } });

    const { result } = renderHook(() => useActivityInput());

    act(() => {
      result.current.startEditingLabel();
    });

    // Simulates selecting all text in the input and pressing Backspace/Delete.
    act(() => {
      result.current.setName('');
    });

    expect(result.current.inputValue).toBe('');
  });

  it('handleLabelCancel restores the original name without calling labelActivity', () => {
    mockGame({ status: 'active', currentActivity: { name: 'Deep work' } });

    const { result } = renderHook(() => useActivityInput());

    act(() => {
      result.current.startEditingLabel();
      result.current.setName('Something typed');
    });

    act(() => {
      result.current.handleLabelCancel();
    });

    expect(result.current.name).toBe('Deep work');
    expect(result.current.isEditingLabel).toBe(false);
    expect(labelActivity).not.toHaveBeenCalled();
  });

  it('handleLabelBlur commits the edited name and exits editing mode', async () => {
    mockGame({ status: 'active', currentActivity: { name: 'Deep work' } });

    const { result } = renderHook(() => useActivityInput());

    act(() => {
      result.current.startEditingLabel();
      result.current.setName('Deeper work');
    });

    await act(async () => {
      await result.current.handleLabelBlur();
    });

    expect(labelActivity).toHaveBeenCalledWith('Deeper work', null);
    expect(result.current.isEditingLabel).toBe(false);
  });

  it('invalidates the today-points query after completing an activity, so the map badge updates immediately (#673)', async () => {
    mockGame({ status: 'active', currentActivity: { name: 'Deep work' } });
    stop.mockResolvedValue({ xp_gained: 10 });

    const { result } = renderHook(() => useActivityInput());

    await act(async () => {
      await result.current.handleToggle();
    });

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['me', 'today-points'],
    });
  });
});
