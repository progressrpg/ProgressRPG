import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchAnnouncements,
  fetchAnnouncementUnreadCount,
  markAllAnnouncementsRead,
  markAnnouncementRead,
} from "./announcements";
import { apiFetch } from "../utils/api";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchAnnouncements", () => {
  it("fetches the announcements list", async () => {
    const response = { results: [] };
    mockedApiFetch.mockResolvedValueOnce(response);

    const result = await fetchAnnouncements();

    expect(mockedApiFetch).toHaveBeenCalledWith("/me/announcements/");
    expect(result).toBe(response);
  });
});

describe("fetchAnnouncementUnreadCount", () => {
  it("fetches the unread count", async () => {
    const response = { unread_count: 3 };
    mockedApiFetch.mockResolvedValueOnce(response);

    const result = await fetchAnnouncementUnreadCount();

    expect(mockedApiFetch).toHaveBeenCalledWith("/me/announcements_unread_count/");
    expect(result).toBe(response);
  });
});

describe("markAnnouncementRead", () => {
  it("posts the announcement id to be marked read", async () => {
    const response = { success: true };
    mockedApiFetch.mockResolvedValueOnce(response);

    const result = await markAnnouncementRead(42);

    expect(mockedApiFetch).toHaveBeenCalledWith("/me/mark_announcement_read/", {
      method: "POST",
      body: JSON.stringify({ announcement_id: 42 }),
    });
    expect(result).toBe(response);
  });
});

describe("markAllAnnouncementsRead", () => {
  it("posts to mark all announcements read", async () => {
    const response = { success: true };
    mockedApiFetch.mockResolvedValueOnce(response);

    const result = await markAllAnnouncementsRead();

    expect(mockedApiFetch).toHaveBeenCalledWith("/me/mark_all_announcements_read/", {
      method: "POST",
    });
    expect(result).toBe(response);
  });
});
