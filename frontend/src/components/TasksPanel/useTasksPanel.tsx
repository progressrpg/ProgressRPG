import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { useTasks, useCreateTask, useUpdateTask, useDeleteTask } from "../../hooks/useTasks";
import { useNotes, useCreateNote } from "../../hooks/useNotes";
import { useGame } from "../../hooks/useGame";
import type { Task } from "../../types";
import type { SortOption } from "../PlayerItemList/PlayerItemList";
import { asArray } from "../../utils/arrayUtils";
import { isCompletable } from "../../utils/completable";
import { formatRewardDuration, formatDueAt, isOverdue } from "../../utils/formatUtils";
import { TASKS_HIDE_COMPLETED_KEY } from "../../utils/userPreferences";

export type ItemRecord = Task & { [key: string]: unknown };

export interface TaskEditSummary {
  created: string;
  modified: string;
  completed: string;
  totalTime: string;
}

export interface ParentGroup {
  parent: ItemRecord;
  children: ItemRecord[];
}

export const isTaskComplete = isCompletable;

export const taskSortOptions: SortOption<ItemRecord>[] = [
  {
    key: "last-worked",
    label: "Last worked",
    compareFn: (a, b) => {
      const ta = a.last_worked_on ? new Date(a.last_worked_on).getTime() : 0;
      const tb = b.last_worked_on ? new Date(b.last_worked_on).getTime() : 0;
      return tb - ta;
    },
  },
  {
    key: "name",
    label: "Name",
    compareFn: (a, b) => (a.name ?? "").localeCompare(b.name ?? ""),
  },
  {
    key: "created",
    label: "Created",
    compareFn: (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  },
  {
    key: "due-date",
    label: "Due date",
    compareFn: (a, b) => {
      const da = a.due_at ? new Date(a.due_at).getTime() : Infinity;
      const db = b.due_at ? new Date(b.due_at).getTime() : Infinity;
      return da - db;
    },
  },
];

function formatTimestamp(timestamp: string | null | undefined): string {
  if (!timestamp) return "-";

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "-";

  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatLastWorkedOn(task: Task): string {
  const timestamp = task?.last_worked_on;
  if (!timestamp) return "No time recorded";

  const workedOn = new Date(timestamp);
  if (Number.isNaN(workedOn.getTime())) return "No time recorded";

  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const startOfWorkedOn = new Date(workedOn.getFullYear(), workedOn.getMonth(), workedOn.getDate());
  const diffDays = Math.round(
    (startOfToday.getTime() - startOfWorkedOn.getTime()) / (24 * 60 * 60 * 1000)
  );

  if (diffDays === 0) return "Last worked on today";
  if (diffDays === 1) return "Last worked on yesterday";
  if (diffDays < 7) return `Last worked on ${diffDays} days ago`;

  const diffWeeks = Math.floor(diffDays / 7);
  return `Last worked on ${diffWeeks} ${diffWeeks === 1 ? "week" : "weeks"} ago`;
}

export function useTasksPanel(openTaskId?: number | null, onOpenNote?: (noteId: number) => void) {
  const navigate = useNavigate();
  const { fetchPlayerAndCharacter, activityTimer, freeTimerLimitSeconds, player } = useGame();
  const isPremium = Boolean(player?.is_premium);

  const { data: tasks, isLoading } = useTasks();
  const { data: notes } = useNotes();
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();
  const createNote = useCreateNote();

  const [newName, setNewName] = useState("");
  const [completionReward, setCompletionReward] = useState<{ taskId: number; xp: number } | null>(null);
  const [hideCompleted, setHideCompleted] = useState(() => {
    try {
      return localStorage.getItem(TASKS_HIDE_COMPLETED_KEY) !== "false";
    } catch {
      return true;
    }
  });
  const [addSubtaskParent, setAddSubtaskParent] = useState<ItemRecord | null>(null);

  useEffect(() => {
    if (!completionReward) return;
    const timer = setTimeout(() => setCompletionReward(null), 4000);
    return () => clearTimeout(timer);
  }, [completionReward]);

  const safeTasks = useMemo(() => asArray(tasks) as ItemRecord[], [tasks]);
  const safeNotes = useMemo(() => asArray(notes), [notes]);

  const getLinkedNoteId = useCallback(
    (task: Task) => safeNotes.find((note) => note.task === task.id)?.id ?? null,
    [safeNotes]
  );

  const topLevelTasks = useMemo(
    () => safeTasks.filter((task) => task.parent == null),
    [safeTasks]
  );

  const groupedTasks = useMemo<ParentGroup[]>(() => {
    const byId = new Map<number, ItemRecord>();
    safeTasks.forEach((task) => byId.set(task.id, task));

    const childrenByParentId = new Map<number, ItemRecord[]>();
    const topLevel: ItemRecord[] = [];

    safeTasks.forEach((task) => {
      const parentId = task.parent;
      const parentTask = parentId != null ? byId.get(parentId) : undefined;
      // Defensive: a task whose parent is missing or itself a subtask
      // (grandparent nesting) renders as top-level rather than vanishing.
      if (parentId == null || !parentTask || parentTask.parent != null) {
        topLevel.push(task);
      } else {
        const siblings = childrenByParentId.get(parentId) ?? [];
        siblings.push(task);
        childrenByParentId.set(parentId, siblings);
      }
    });

    const visibleTopLevel = hideCompleted
      ? topLevel.filter((task) => !isTaskComplete(task))
      : topLevel;

    if (hideCompleted && openTaskId != null && !visibleTopLevel.some((task) => task.id === openTaskId)) {
      const deepLinkedTask = topLevel.find((task) => task.id === openTaskId);
      if (deepLinkedTask) visibleTopLevel.push(deepLinkedTask);
    }

    return visibleTopLevel.map((parent) => {
      const children = childrenByParentId.get(parent.id) ?? [];
      return {
        parent,
        children: hideCompleted ? children.filter((child) => !isTaskComplete(child)) : children,
      };
    });
  }, [safeTasks, hideCompleted, openTaskId]);

  const visibleTasks = useMemo(
    () => groupedTasks.flatMap((group) => [group.parent, ...group.children]),
    [groupedTasks]
  );

  const childrenByGroupParentId = useMemo(
    () => new Map(groupedTasks.map((group) => [group.parent.id, group.children])),
    [groupedTasks]
  );

  const getChildren = useCallback(
    (task: ItemRecord): ItemRecord[] => childrenByGroupParentId.get(task.id) ?? [],
    [childrenByGroupParentId]
  );

  const handleCreateNoteForTask = useCallback(
    (task: Task) => {
      createNote.mutate(
        { title: task.name, body: "", task: task.id },
        { onSuccess: (note) => onOpenNote?.(note.id) }
      );
    },
    [createNote, onOpenNote]
  );

  const toggleHideCompleted = useCallback(() => {
    setHideCompleted((current) => {
      const next = !current;
      try {
        localStorage.setItem(TASKS_HIDE_COMPLETED_KEY, String(next));
      } catch {
        // Ignore persistence failures.
      }
      return next;
    });
  }, []);

  const handleCreateTask = useCallback(
    (name: string, options?: { parent?: number | null; due_at?: string | null }) => {
      const trimmed = name.trim();
      if (!trimmed) return;
      createTask.mutate({
        name: trimmed,
        ...(options?.parent !== undefined ? { parent: options.parent } : {}),
        ...(options?.due_at !== undefined ? { due_at: options.due_at } : {}),
      });
      setNewName("");
      setAddSubtaskParent(null);
    },
    [createTask]
  );

  const handleSubmitForm = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      handleCreateTask(newName, { parent: addSubtaskParent?.id ?? undefined });
    },
    [handleCreateTask, newName, addSubtaskParent]
  );

  const startAddSubtask = useCallback((task: ItemRecord) => {
    setAddSubtaskParent(task);
  }, []);

  const clearAddSubtaskParent = useCallback(() => {
    setAddSubtaskParent(null);
  }, []);

  const handleEdit = useCallback(
    (task: ItemRecord, name: string, callbacks?: { onSuccess?: () => void; onError?: () => void }) => {
      updateTask.mutate({ id: task.id, data: { name } }, callbacks);
    },
    [updateTask]
  );

  const handleDelete = useCallback(
    (task: Task) => {
      deleteTask.mutate(task.id);
    },
    [deleteTask]
  );

  const handleToggleComplete = useCallback(
    (task: Task) => {
      const completing = !isTaskComplete(task);
      updateTask.mutate(
        {
          id: task.id,
          data: {
            is_complete: completing,
            completed_at: completing ? new Date().toISOString() : null,
          },
        },
        {
          onSuccess: (data) => {
            if (data.completion_xp_gained > 0) {
              setCompletionReward({ taskId: task.id, xp: data.completion_xp_gained });
              fetchPlayerAndCharacter();
            }
          },
        }
      );
    },
    [fetchPlayerAndCharacter, updateTask]
  );

  const handleStartTask = useCallback(
    async (task: Task) => {
      const name = task.name;
      if (!name || activityTimer?.status === "active") return;

      await activityTimer?.startActivity({
        text: name,
        taskId: task.id,
        limitSeconds: isPremium ? null : freeTimerLimitSeconds,
      });
      navigate("/timer");
    },
    [activityTimer, freeTimerLimitSeconds, isPremium, navigate]
  );

  const getTaskMeta = useCallback(
    (task: Task) => ({
      lastWorkedOn: formatLastWorkedOn(task),
      completionXp: completionReward?.taskId === task.id ? completionReward.xp : null,
      dueAt: formatDueAt(task.due_at),
      isOverdue: isOverdue(task.due_at, isTaskComplete(task)),
    }),
    [completionReward]
  );

  const getTaskEditSummary = useCallback((task: Task): TaskEditSummary => {
    const complete = isTaskComplete(task);
    const wasModified =
      Boolean(task.last_updated) &&
      Boolean(task.created_at) &&
      Math.abs(new Date(task.last_updated).getTime() - new Date(task.created_at).getTime()) > 2000;

    return {
      created: formatTimestamp(task.created_at),
      modified: wasModified ? formatTimestamp(task.last_updated) : "-",
      completed: complete ? formatTimestamp(task.completed_at) : "-",
      totalTime: formatRewardDuration(task.total_time),
    };
  }, []);

  return {
    isLoading,
    newName,
    setNewName,
    hideCompleted,
    visibleTasks,
    groupedTasks,
    getChildren,
    topLevelTasks,
    addSubtaskParent,
    startAddSubtask,
    clearAddSubtaskParent,
    handleCreateTask,
    handleSubmitForm,
    handleEdit,
    handleDelete,
    handleToggleComplete,
    handleStartTask,
    toggleHideCompleted,
    getTaskMeta,
    getTaskEditSummary,
    getLinkedNoteId,
    handleCreateNoteForTask,
    updateTask,
  };
}
