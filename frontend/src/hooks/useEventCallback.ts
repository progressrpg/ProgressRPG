import { useEffect, useRef, useCallback } from 'react';

/**
 * Returns a stable function identity that always calls the latest `fn`.
 *
 * Lets an effect invoke fresh, non-reactive logic (e.g. a fetch that sets
 * state) via a ref instead of capturing `fn` directly, since the latter
 * trips `react-hooks/set-state-in-effect` even when `fn` only sets state
 * after an `await`.
 */
export function useEventCallback<Args extends unknown[], Return>(
  fn: (...args: Args) => Return
): (...args: Args) => Return {
  const ref = useRef(fn);

  useEffect(() => {
    ref.current = fn;
  });

  return useCallback((...args: Args) => ref.current(...args), []);
}
