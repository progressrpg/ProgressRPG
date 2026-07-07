import { useMemo } from "react";

import { useGame } from "./useGame";
import { useTasks } from "./useTasks";
import { useFeatureFlag } from "./useFeatureFlag";
import type { SearchEntity } from "../components/EntitySearchInput/useEntitySearchInput";
import type { CharacterActivity, PlayerActivity, Task } from "../types";

function toEpoch(value: string | null | undefined): number {
  return value ? new Date(value).getTime() : 0;
}

function toNameKey(name: string): string {
  return name.trim().replace(/\s+/g, " ").toLowerCase();
}

type RankedEntity = SearchEntity & { recency: number };

/** How many rows the default (empty-query) view shows, most recent first. */
const MAX_DEFAULT_ENTRIES = 4;

/**
 * Builds the default (empty-query) view for the unified activity list:
 * incomplete tasks (collapsing any activities linked to them), plus
 * standalone activities that aren't linked to an incomplete task, sorted
 * by recency and capped to the most recent MAX_DEFAULT_ENTRIES rows.
 */
export function useDefaultActivityEntries(): SearchEntity[] {
  const { playerActivities, characterActivities } = useGame();
  const hasTasksFeature = useFeatureFlag("tasksFeature");
  const { data: tasks } = useTasks({ enabled: hasTasksFeature });

  return useMemo(() => {
    const rowsByTaskId = new Map<number, RankedEntity>();
    const completedTaskIds = new Set<number>();

    (tasks ?? []).forEach((task: Task) => {
      if (task.is_complete || task.completed_at) {
        completedTaskIds.add(task.id);
        return;
      }
      rowsByTaskId.set(task.id, {
        id: `task-${task.id}`,
        name: task.name,
        nameKey: toNameKey(task.name),
        taskId: task.id,
        source: "task",
        recency: toEpoch(task.last_worked_on ?? task.created_at),
      });
    });

    const standalone: RankedEntity[] = [];

    (playerActivities ?? []).forEach((activity: PlayerActivity) => {
      const name = (activity.name || "").trim();
      if (!name) return;
      if (activity.task != null && completedTaskIds.has(activity.task)) return;

      const recency = toEpoch(activity.completed_at ?? activity.last_updated ?? activity.created_at);
      const linkedRow = activity.task != null ? rowsByTaskId.get(activity.task) : undefined;

      if (linkedRow) {
        if (recency > linkedRow.recency) linkedRow.recency = recency;
        return;
      }

      standalone.push({
        id: `activity-${activity.id}`,
        name,
        nameKey: toNameKey(name),
        taskId: null,
        source: "activity",
        recency,
      });
    });

    (characterActivities ?? []).forEach((activity: CharacterActivity) => {
      const name = (activity.name || activity.kind || "").trim();
      if (!name) return;

      standalone.push({
        id: `character-activity-${activity.id}`,
        name,
        nameKey: toNameKey(name),
        taskId: null,
        source: "activity",
        recency: toEpoch(activity.completed_at ?? activity.last_updated ?? activity.created_at),
      });
    });

    return [...rowsByTaskId.values(), ...standalone]
      .sort((a, b) => b.recency - a.recency)
      .slice(0, MAX_DEFAULT_ENTRIES)
      .map((entity): SearchEntity => ({
        id: entity.id,
        name: entity.name,
        nameKey: entity.nameKey,
        taskId: entity.taskId,
        source: entity.source,
      }));
  }, [playerActivities, characterActivities, tasks]);
}
