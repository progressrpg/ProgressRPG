import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import useUnloadWarning from './useUnloadWarning';

describe('useUnloadWarning', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('registers a beforeunload handler while active and removes it on deactivation', () => {
    const addSpy = vi.spyOn(window, 'addEventListener');
    const removeSpy = vi.spyOn(window, 'removeEventListener');

    const { rerender } = renderHook(({ active }) => useUnloadWarning(active), {
      initialProps: { active: true },
    });

    expect(addSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function));

    rerender({ active: false });

    expect(removeSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function));
  });

  it('does not register a handler when inactive', () => {
    const addSpy = vi.spyOn(window, 'addEventListener');

    renderHook(() => useUnloadWarning(false));

    expect(addSpy).not.toHaveBeenCalledWith('beforeunload', expect.any(Function));
  });

  it('prevents default and clears returnValue on the beforeunload event', () => {
    renderHook(() => useUnloadWarning(true));

    const event = new Event('beforeunload') as BeforeUnloadEvent;
    const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

    window.dispatchEvent(event);

    expect(preventDefaultSpy).toHaveBeenCalled();
    expect(event.returnValue).toBe('');
  });
});
