import { useCallback, useMemo, useState } from "react";

import { useNotes, useCreateNote, useUpdateNote, useDeleteNote } from "../../hooks/useNotes";
import { useTasks } from "../../hooks/useTasks";
import type { Note } from "../../types";
import { asArray } from "../../utils/arrayUtils";

const NO_TASK_VALUE = "";

function parseTaskId(value: string): number | null {
  return value === NO_TASK_VALUE ? null : Number(value);
}

export function useNotesPanel() {
  const { data: notes, isLoading } = useNotes();
  const { data: tasks } = useTasks();
  const createNote = useCreateNote();
  const updateNote = useUpdateNote();
  const deleteNote = useDeleteNote();

  const [newTitle, setNewTitle] = useState("");
  const [newBody, setNewBody] = useState("");
  const [newTaskId, setNewTaskId] = useState<string>(NO_TASK_VALUE);

  const [activeNote, setActiveNote] = useState<Note | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editBody, setEditBody] = useState("");
  const [editTaskId, setEditTaskId] = useState<string>(NO_TASK_VALUE);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const visibleNotes = useMemo(() => asArray(notes), [notes]);
  const taskOptions = useMemo(() => asArray(tasks), [tasks]);

  const getTaskName = useCallback(
    (taskId: number | null) => taskOptions.find((task) => task.id === taskId)?.name ?? null,
    [taskOptions]
  );

  const handleCreate = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmedTitle = newTitle.trim();
      if (!trimmedTitle) return;

      createNote.mutate({
        title: trimmedTitle,
        body: newBody.trim(),
        task: parseTaskId(newTaskId),
      });
      setNewTitle("");
      setNewBody("");
      setNewTaskId(NO_TASK_VALUE);
    },
    [createNote, newBody, newTaskId, newTitle]
  );

  const openNote = useCallback((note: Note) => {
    setActiveNote(note);
    setEditTitle(note.title);
    setEditBody(note.body);
    setEditTaskId(note.task === null ? NO_TASK_VALUE : String(note.task));
    setConfirmingDelete(false);
  }, []);

  const closeNote = useCallback(() => {
    setActiveNote(null);
    setConfirmingDelete(false);
  }, []);

  const handleEditSave = useCallback(() => {
    if (!activeNote) return;
    const trimmedTitle = editTitle.trim();
    if (!trimmedTitle) return;

    updateNote.mutate({
      id: activeNote.id,
      data: {
        title: trimmedTitle,
        body: editBody.trim(),
        task: parseTaskId(editTaskId),
      },
    });
    setActiveNote(null);
  }, [activeNote, editBody, editTaskId, editTitle, updateNote]);

  const handleDeleteRequest = useCallback(() => setConfirmingDelete(true), []);

  const cancelDeleteRequest = useCallback(() => setConfirmingDelete(false), []);

  const handleDeleteConfirm = useCallback(() => {
    if (!activeNote) return;
    deleteNote.mutate(activeNote.id);
    setActiveNote(null);
    setConfirmingDelete(false);
  }, [activeNote, deleteNote]);

  return {
    isLoading,
    visibleNotes,
    taskOptions,
    getTaskName,
    newTitle,
    setNewTitle,
    newBody,
    setNewBody,
    newTaskId,
    setNewTaskId,
    handleCreate,
    activeNote,
    editTitle,
    setEditTitle,
    editBody,
    setEditBody,
    editTaskId,
    setEditTaskId,
    confirmingDelete,
    openNote,
    closeNote,
    handleEditSave,
    handleDeleteRequest,
    cancelDeleteRequest,
    handleDeleteConfirm,
  };
}
