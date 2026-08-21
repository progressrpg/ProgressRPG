import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCreateNote, useDeleteNote, useNotes, useUpdateNote } from "./useNotes";
import type { Note } from "../types";

const mockFetchNotes = vi.fn();
const mockCreateNote = vi.fn();
const mockUpdateNote = vi.fn();
const mockDeleteNote = vi.fn();

vi.mock("../api/notes", () => ({
  fetchNotes: (...args: unknown[]) => mockFetchNotes(...args),
  createNote: (...args: unknown[]) => mockCreateNote(...args),
  updateNote: (...args: unknown[]) => mockUpdateNote(...args),
  deleteNote: (...args: unknown[]) => mockDeleteNote(...args),
}));

const note = (id: number): Note => ({ id, text: `Note ${id}` } as unknown as Note);

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useNotes", () => {
  beforeEach(() => {
    mockFetchNotes.mockReset();
    mockCreateNote.mockReset();
    mockUpdateNote.mockReset();
    mockDeleteNote.mockReset();
  });

  it("fetches notes by default", async () => {
    mockFetchNotes.mockResolvedValue([note(1)]);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useNotes(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([note(1)]);
  });

  it("does not fetch when disabled via options", () => {
    const { wrapper } = makeWrapper();
    renderHook(() => useNotes({ enabled: false }), { wrapper });
    expect(mockFetchNotes).not.toHaveBeenCalled();
  });

  it("invalidates notes after creating one", async () => {
    mockCreateNote.mockResolvedValue(note(2));
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateNote(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ text: "New" } as unknown as Partial<Note>);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["notes"] });
  });

  it("passes id and data through to updateNote", async () => {
    mockUpdateNote.mockResolvedValue(note(1));
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useUpdateNote(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ id: 1, data: { text: "Renamed" } as unknown as Partial<Note> });
    });

    expect(mockUpdateNote).toHaveBeenCalledWith(1, { text: "Renamed" });
  });

  it("optimistically removes a deleted note and rolls back on failure", async () => {
    mockDeleteNote.mockRejectedValue(new Error("boom"));
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["notes"], [note(1), note(2)]);

    const { result } = renderHook(() => useDeleteNote(), { wrapper });
    await act(async () => {
      try {
        await result.current.mutateAsync(1);
      } catch {
        // expected
      }
    });

    expect(queryClient.getQueryData(["notes"])).toEqual([note(1), note(2)]);
  });

  it("keeps an optimistically deleted note removed on success", async () => {
    mockDeleteNote.mockResolvedValue(undefined);
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["notes"], [note(1), note(2)]);

    const { result } = renderHook(() => useDeleteNote(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync(1);
    });

    expect(queryClient.getQueryData(["notes"])).toEqual([note(2)]);
  });
});
