// src/hooks/useNotes.ts

import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { updateNote, deleteNote, fetchNotes, createNote } from "../api/notes";
import type { Note } from "../types";

export function useNotes(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["notes"],
    queryFn: fetchNotes,
    enabled: options?.enabled ?? true,
    staleTime: 30_000,
  });
}

export function useCreateNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createNote,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}

export function useUpdateNote() {
  const qc = useQueryClient();

  return useMutation<Note, Error, { id: number; data: Partial<Note> }>({
    mutationFn: ({ id, data }) => updateNote(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}

export function useDeleteNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteNote,
    onMutate: async (noteId: number) => {
      await queryClient.cancelQueries({ queryKey: ["notes"] });

      const previousNotes = queryClient.getQueryData<Note[]>(["notes"]);

      queryClient.setQueryData<Note[]>(["notes"], (old = []) =>
        old.filter((note) => note.id !== noteId)
      );
      return { previousNotes };
    },

    onError: (_err: unknown, _noteId: number, context: { previousNotes?: Note[] } | undefined) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(["notes"], context.previousNotes);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}
