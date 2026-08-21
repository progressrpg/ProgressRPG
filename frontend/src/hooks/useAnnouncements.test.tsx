import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useAnnouncements,
  useAnnouncementUnreadCount,
  useMarkAllAnnouncementsRead,
  useMarkAnnouncementRead,
} from "./useAnnouncements";

const mockFetchAnnouncements = vi.fn();
const mockFetchAnnouncementUnreadCount = vi.fn();
const mockMarkAnnouncementRead = vi.fn();
const mockMarkAllAnnouncementsRead = vi.fn();

vi.mock("../api/announcements", () => ({
  fetchAnnouncements: (...args: unknown[]) => mockFetchAnnouncements(...args),
  fetchAnnouncementUnreadCount: (...args: unknown[]) => mockFetchAnnouncementUnreadCount(...args),
  markAnnouncementRead: (...args: unknown[]) => mockMarkAnnouncementRead(...args),
  markAllAnnouncementsRead: (...args: unknown[]) => mockMarkAllAnnouncementsRead(...args),
}));

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useAnnouncements", () => {
  beforeEach(() => {
    mockFetchAnnouncements.mockReset();
    mockFetchAnnouncementUnreadCount.mockReset();
    mockMarkAnnouncementRead.mockReset();
    mockMarkAllAnnouncementsRead.mockReset();
  });

  it("fetches announcements when enabled (default)", async () => {
    mockFetchAnnouncements.mockResolvedValue([{ id: 1 }]);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useAnnouncements(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([{ id: 1 }]);
  });

  it("does not fetch announcements when explicitly disabled", () => {
    const { wrapper } = makeWrapper();
    renderHook(() => useAnnouncements(false), { wrapper });
    expect(mockFetchAnnouncements).not.toHaveBeenCalled();
  });

  it("fetches the unread count", async () => {
    mockFetchAnnouncementUnreadCount.mockResolvedValue(3);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useAnnouncementUnreadCount(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBe(3);
  });

  it("invalidates both announcements and unread count after marking one read", async () => {
    mockMarkAnnouncementRead.mockResolvedValue(undefined);
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useMarkAnnouncementRead(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync(1);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["announcements"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["announcements", "unreadCount"] });
  });

  it("invalidates both announcements and unread count after marking all read", async () => {
    mockMarkAllAnnouncementsRead.mockResolvedValue(undefined);
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useMarkAllAnnouncementsRead(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["announcements"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["announcements", "unreadCount"] });
  });
});
