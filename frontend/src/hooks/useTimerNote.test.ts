import React from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useTimerNote } from "./useTimerNote";

const mockFetchNoteFor = vi.fn();
const mockCreateNote = vi.fn();
const mockUpdateNote = vi.fn();

vi.mock("../api/notes", () => ({
  fetchNoteFor: (...args: unknown[]) => mockFetchNoteFor(...args),
  createNote: (...args: unknown[]) => mockCreateNote(...args),
  updateNote: (...args: unknown[]) => mockUpdateNote(...args),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return React.createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useTimerNote", () => {
  beforeEach(() => {
    mockFetchNoteFor.mockReset();
    mockCreateNote.mockReset();
    mockUpdateNote.mockReset();
  });

  it("is disabled with no task or activity linked", () => {
    const { result } = renderHook(() => useTimerNote({ taskId: null, activityId: null }), { wrapper });

    expect(result.current.enabled).toBe(false);
    expect(mockFetchNoteFor).not.toHaveBeenCalled();
  });

  it("fetches and pre-populates the body from an existing linked note", async () => {
    mockFetchNoteFor.mockResolvedValue({
      id: 9,
      title: "",
      body: "Left off at step 3",
      player: 1,
      task: 5,
      activity: null,
      created_at: "",
      last_updated: "",
    });

    const { result } = renderHook(() => useTimerNote({ taskId: 5, activityId: null }), { wrapper });

    await waitFor(() => expect(result.current.value).toBe("Left off at step 3"));
    expect(mockFetchNoteFor).toHaveBeenCalledWith({ task: 5 });
  });

  it("starts blank when there is no linked note yet", async () => {
    mockFetchNoteFor.mockResolvedValue(null);

    const { result } = renderHook(() => useTimerNote({ taskId: null, activityId: 7 }), { wrapper });

    await waitFor(() => expect(mockFetchNoteFor).toHaveBeenCalledWith({ activity: 7 }));
    expect(result.current.value).toBe("");
  });

  it("creates a note on save when none exists and text is non-blank", async () => {
    mockFetchNoteFor.mockResolvedValue(null);
    mockCreateNote.mockResolvedValue({
      id: 3,
      title: "",
      body: "washing up",
      player: 1,
      task: null,
      activity: 7,
      created_at: "",
      last_updated: "",
    });

    const { result } = renderHook(() => useTimerNote({ taskId: null, activityId: 7 }), { wrapper });
    await waitFor(() => expect(mockFetchNoteFor).toHaveBeenCalled());

    act(() => result.current.setValue("washing up"));
    await act(async () => {
      await result.current.save();
    });

    expect(mockCreateNote).toHaveBeenCalledWith({ body: "washing up", activity: 7 });
  });

  it("does not create a note on save when the field is only whitespace", async () => {
    mockFetchNoteFor.mockResolvedValue(null);

    const { result } = renderHook(() => useTimerNote({ taskId: 5, activityId: null }), { wrapper });
    await waitFor(() => expect(mockFetchNoteFor).toHaveBeenCalled());

    act(() => result.current.setValue("   "));
    await act(async () => {
      await result.current.save();
    });

    expect(mockCreateNote).not.toHaveBeenCalled();
  });

  it("updates the existing note in place on save", async () => {
    mockFetchNoteFor.mockResolvedValue({
      id: 9,
      title: "",
      body: "old text",
      player: 1,
      task: 5,
      activity: null,
      created_at: "",
      last_updated: "",
    });
    mockUpdateNote.mockResolvedValue({
      id: 9,
      title: "",
      body: "new text",
      player: 1,
      task: 5,
      activity: null,
      created_at: "",
      last_updated: "",
    });

    const { result } = renderHook(() => useTimerNote({ taskId: 5, activityId: null }), { wrapper });
    await waitFor(() => expect(result.current.value).toBe("old text"));

    act(() => result.current.setValue("new text"));
    await act(async () => {
      await result.current.save();
    });

    expect(mockUpdateNote).toHaveBeenCalledWith(9, { body: "new text" });
  });

  it("clears an existing note's body rather than leaving whitespace when blanked", async () => {
    mockFetchNoteFor.mockResolvedValue({
      id: 9,
      title: "",
      body: "old text",
      player: 1,
      task: 5,
      activity: null,
      created_at: "",
      last_updated: "",
    });
    mockUpdateNote.mockResolvedValue({
      id: 9,
      title: "",
      body: "",
      player: 1,
      task: 5,
      activity: null,
      created_at: "",
      last_updated: "",
    });

    const { result } = renderHook(() => useTimerNote({ taskId: 5, activityId: null }), { wrapper });
    await waitFor(() => expect(result.current.value).toBe("old text"));

    act(() => result.current.setValue("   "));
    await act(async () => {
      await result.current.save();
    });

    expect(mockUpdateNote).toHaveBeenCalledWith(9, { body: "" });
  });
});
