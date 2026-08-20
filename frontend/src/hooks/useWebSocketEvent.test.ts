import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useWebSocketEvent } from "./useWebSocketEvent";

const mockAddEventHandler = vi.fn();

vi.mock("./useWebSocket", () => ({
  useWebSocket: () => ({ addEventHandler: mockAddEventHandler }),
}));

describe("useWebSocketEvent", () => {
  beforeEach(() => {
    mockAddEventHandler.mockReset();
  });

  it("registers the callback and cleans up the returned remove function on unmount", () => {
    const remove = vi.fn();
    mockAddEventHandler.mockReturnValue(remove);
    const callback = vi.fn();

    const { unmount } = renderHook(() => useWebSocketEvent(callback));

    expect(mockAddEventHandler).toHaveBeenCalledWith(callback);
    expect(remove).not.toHaveBeenCalled();

    unmount();

    expect(remove).toHaveBeenCalled();
  });

  it("does not register when the callback is null", () => {
    renderHook(() => useWebSocketEvent(null));
    expect(mockAddEventHandler).not.toHaveBeenCalled();
  });

  it("re-registers when the callback identity changes", () => {
    const removeA = vi.fn();
    const removeB = vi.fn();
    mockAddEventHandler.mockReturnValueOnce(removeA).mockReturnValueOnce(removeB);

    const { rerender } = renderHook(({ cb }) => useWebSocketEvent(cb), {
      initialProps: { cb: vi.fn() },
    });

    rerender({ cb: vi.fn() });

    expect(removeA).toHaveBeenCalled();
    expect(mockAddEventHandler).toHaveBeenCalledTimes(2);
  });
});
