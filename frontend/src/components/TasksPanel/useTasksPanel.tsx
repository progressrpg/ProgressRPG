import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { useTasks, useCreateTask, useUpdateTask, useDeleteTask } from "../../hooks/useTasks";
import { useGame } from "../../hooks/useGame";
import type { Task } from "../../types";
import type { SortOption } from "../PlayerItemList/PlayerItemList";
import { asArray } from "../../utils/arrayUtils";
import { isCompletable } from "../../utils/completable";
import { formatRewardDuration } from "../../utils/formatUtils";
import { TASKS_HIDE_COMPLETED_KEY } from "../../utils/userPreferences";

export interface TaskEditSummary {
  created: string;
  modified: string;
  completed: string;
  totalTime: string;
}

export const isTaskComplete = isCompletable;

export const taskSortOptions: SortOption<Task>[] = [
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

export function useTasksPanel() {
  const navigate = useNavigate();
  const { fetchPlayerAndCharacter, activityTimer, freeTimerLimitSeconds, player } = useGame();
  const isPremium = Boolean(player?.is_premium);

  const { data: tasks, isLoading } = useTasks();
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  const [newName, setNewName] = useState("");
  const [completionReward, setCompletionReward] = useState<{ taskId: number; xp: number } | null>(null);
  const [hideCompleted, setHideCompleted] = useState(() => {
    try {
      return localStorage.getItem(TASKS_HIDE_COMPLETED_KEY) !== "false";
    } catch {
      return true;
    }
  });

  useEffect(() => {
    if (!completionReward) return;
    const timer = setTimeout(() => setCompletionReward(null), 4000);
    return () => clearTimeout(timer);
  }, [completionReward]);

  const safeTasks = useMemo(() => asArray(tasks), [tasks]);

  const visibleTasks = useMemo(
    () => (hideCompleted ? safeTasks.filter((task) => !isTaskComplete(task)) : safeTasks),
    [hideCompleted, safeTasks]
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
    (name: string) => {
      const trimmed = name.trim();
      if (!trimmed) return;
      createTask.mutate({ name: trimmed });
      setNewName("");
    },
    [createTask]
  );

  const handleSubmitForm = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      handleCreateTask(newName);
    },
    [handleCreateTask, newName]
  );

  const handleEdit = useCallback(
    (task: Task, name: string) => {
      updateTask.mutate({ id: task.id, data: { name } });
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
    handleCreateTask,
    handleSubmitForm,
    handleEdit,
    handleDelete,
    handleToggleComplete,
    handleStartTask,
    toggleHideCompleted,
    getTaskMeta,
    getTaskEditSummary,
  };
}
