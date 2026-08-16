// src/hooks/useTimerNote.ts
import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchNoteFor, createNote, updateNote } from "../api/notes";

interface TimerNoteLink {
  taskId: number | null;
  activityId: number | null;
}

/**
 * Note linked to whatever is being timed — a Task if one's attached, else
 * the reusable Activity "type" (catalog entry) for an ad-hoc/unlabelled
 * activity. Either identity is stable across separate start/stop cycles of
 * the same thing, so the note (and its id, once created) persists with it.
 */
export function useTimerNote({ taskId, activityId }: TimerNoteLink) {
  const queryClient = useQueryClient();
  const linkType = taskId != null ? "task" : activityId != null ? "activity" : null;
  const linkId = linkType === "task" ? taskId : activityId;
  const enabled = linkType !== null;

  const { data: note } = useQuery({
    queryKey: ["notes", "timer-link", linkType, linkId],
    queryFn: () =>
      fetchNoteFor(linkType === "task" ? { task: linkId as number } : { activity: linkId as number }),
    enabled,
  });

  const [value, setValue] = useState("");
  const [noteId, setNoteId] = useState<number | null>(null);
  const [lastSaved, setLastSaved] = useState("");

  // Re-sync editable text whenever the linked entity (or its fetched note)
  // changes — e.g. relabelling the running timer onto a different task.
  // Adjusted during render (not an effect) per React's "adjusting state when
  // a prop changes" pattern — state, not a ref, tracks the last-synced
  // identity so this only fires once per actual change.
  const syncKey = enabled ? `${linkType}:${linkId}:${note?.id ?? "none"}:${note?.body ?? ""}` : null;
  const [lastSyncKey, setLastSyncKey] = useState<string | null>(null);
  if (syncKey !== null && syncKey !== lastSyncKey) {
    setLastSyncKey(syncKey);
    const body = note?.body ?? "";
    setValue(body);
    setNoteId(note?.id ?? null);
    setLastSaved(body);
  }

  const save = useCallback(async () => {
    if (!enabled) return;
    const trimmed = value.trim();
    if (trimmed === lastSaved.trim()) return;

    if (noteId !== null) {
      const updated = await updateNote(noteId, { body: trimmed });
      setLastSaved(updated.body);
    } else if (trimmed) {
      const created = await createNote(
        linkType === "task" ? { body: trimmed, task: linkId } : { body: trimmed, activity: linkId }
      );
      setNoteId(created.id);
      setLastSaved(created.body);
    } else {
      return;
    }

    queryClient.invalidateQueries({ queryKey: ["notes"] });
  }, [enabled, value, lastSaved, noteId, linkType, linkId, queryClient]);

  return { value, setValue, save, enabled };
}
