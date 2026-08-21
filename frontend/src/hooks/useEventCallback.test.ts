import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useEventCallback } from "./useEventCallback";

describe("useEventCallback", () => {
  it("returns a stable function identity across re-renders", () => {
    const { result, rerender } = renderHook(({ fn }) => useEventCallback(fn), {
      initialProps: { fn: () => 1 },
    });

    const first = result.current;
    rerender({ fn: () => 2 });

    expect(result.current).toBe(first);
  });

  it("always invokes the latest function passed in, even after the identity is captured", () => {
    const { result, rerender } = renderHook(({ fn }) => useEventCallback(fn), {
      initialProps: { fn: (n: number) => n + 1 },
    });

    const stable = result.current;
    expect(stable(1)).toBe(2);

    rerender({ fn: (n: number) => n * 10 });

    expect(stable(1)).toBe(10);
  });
});
