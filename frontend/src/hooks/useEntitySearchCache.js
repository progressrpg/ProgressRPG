import { useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchActivities } from "../api/activities";
import { fetchTasks } from "../api/tasks";

function isTaskComplete(task) {
  return Boolean(task?.completed_at ?? task?.is_complete);
}

const ACTIVITY_LIST_CACHE_KEY = ["entity-search", "activity", "activities"];
const TASK_LIST_CACHE_KEY = ["entity-search", "activity", "tasks"];

const ENTITY_CONFIG = {
  activity: {
    queryKey: ["entity-search", "activity"],
    queryFn: async () => {
      const [activities, tasks] = await Promise.all([
        fetchActivities(),
        fetchTasks().catch(() => []),
      ]);

      const incompleteTasks = Array.isArray(tasks)
        ? tasks.filter((task) => !isTaskComplete(task))
        : [];

      return {
        activities: Array.isArray(activities) ? activities : [],
        tasks: incompleteTasks,
      };
    },
  },
};

function normalizeEntityName(value) {
  return typeof value === "string" ? value.trim().replace(/\s+/g, " ") : "";
}

function getEntityNameKey(name) {
  return normalizeEntityName(name).toLowerCase();
}

function getEntityCacheKey(entity) {
  const source = entity?.source || "activity";
  return `${source}:${getEntityNameKey(entity?.name)}`;
}

function normalizeActivityEntity(activity) {
  const name = normalizeEntityName(activity?.name);
  if (!name) return null;

  return {
    id: activity?.id ?? `activity-${name.toLowerCase()}`,
    name,
    taskId: null,
    completedAt: activity?.completed_at ?? null,
    source: "activity",
    isOptimistic: Boolean(activity?.isOptimistic),
    frequency: activity?.frequency ?? 0,
  };
}

function normalizeTaskEntity(task) {
  const name = normalizeEntityName(task?.name);
  if (!name) return null;

  return {
    id: task?.id ?? `task-${name.toLowerCase()}`,
    name,
    taskId: task?.id ?? null,
    completedAt: task?.updated_at ?? task?.created_at ?? null,
    source: "task",
    isOptimistic: Boolean(task?.isOptimistic),
    frequency: task?.frequency ?? 0,
  };
}

function normalizeAnyEntity(entity) {
  if (entity?.source === "task") {
    return normalizeTaskEntity(entity);
  }

  if (entity?.source === "activity") {
    return normalizeActivityEntity(entity);
  }

  // Activity records include completed_at; tasks generally do not.
  if (
    Object.prototype.hasOwnProperty.call(entity ?? {}, "duration") ||
    Object.prototype.hasOwnProperty.call(entity ?? {}, "started_at") ||
    Object.prototype.hasOwnProperty.call(entity ?? {}, "xp_gained")
  ) {
    return normalizeActivityEntity(entity);
  }

  return normalizeTaskEntity(entity);
}

function normalizeStringEntity(type, name) {
  if (type === "activity") {
    return normalizeActivityEntity({ name, isOptimistic: true });
  }

  return null;
}

function getEntityNormalizer(type) {
  if (type === "activity") {
    return normalizeAnyEntity;
  }

  throw new Error(`Unsupported entity search type: ${type}`);
}

function sortEntitiesByRecency(entities) {
  return [...entities].sort((left, right) => {
    const leftTime = left.completedAt ? new Date(left.completedAt).getTime() : 0;
    const rightTime = right.completedAt ? new Date(right.completedAt).getTime() : 0;
    // Sort by frequency first (most used), then recency, then name
    if (left.frequency !== right.frequency) {
      return right.frequency - left.frequency;
    }

    if (leftTime !== rightTime) {
      return rightTime - leftTime;
    }

    return left.name.localeCompare(right.name);
  });
}

function dedupeEntities(entities) {
  const byName = new Map();

  sortEntitiesByRecency(entities).forEach((entity) => {
    const key = getEntityCacheKey(entity);
    if (!byName.has(key)) {
      byName.set(key, entity);
    }
  });

  return [...byName.values()];
}

export function useEntitySearchCache(type) {
  const queryClient = useQueryClient();
  const config = ENTITY_CONFIG[type];
  const normalizeEntity = useMemo(() => getEntityNormalizer(type), [type]);

  if (!config) {
    throw new Error(`Unsupported entity search type: ${type}`);
  }

  const query = useQuery({
    queryKey: config.queryKey,
    queryFn: async () => {
      const data = await config.queryFn();

      if (type !== "activity") {
        const normalizedEntities = Array.isArray(data)
          ? data.map(normalizeEntity).filter(Boolean)
          : [];
        return dedupeEntities(normalizedEntities);
      }

      const normalizedActivities = (data?.activities ?? [])
        .map(normalizeActivityEntity)
        .filter(Boolean);
      const normalizedTasks = (data?.tasks ?? [])
        .map(normalizeTaskEntity)
        .filter(Boolean);

      const dedupedActivities = dedupeEntities(normalizedActivities);
      const dedupedTasks = dedupeEntities(normalizedTasks);

      queryClient.setQueryData(ACTIVITY_LIST_CACHE_KEY, dedupedActivities);
      queryClient.setQueryData(TASK_LIST_CACHE_KEY, dedupedTasks);

      return dedupeEntities([...dedupedActivities, ...dedupedTasks]);
    },
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: Number.POSITIVE_INFINITY,
    refetchOnWindowFocus: false,
  });

  const addEntityToCache = useCallback(
    (entityInput) => {
      const entity =
        typeof entityInput === "string"
          ? normalizeStringEntity(type, entityInput)
          : normalizeEntity(entityInput);

      if (!entity) {
        return null;
      }

      queryClient.setQueryData(config.queryKey, (currentEntities = []) =>
        dedupeEntities(
          currentEntities.map((e) =>
            getEntityCacheKey(e) === getEntityCacheKey(entity)
              ? { ...e, frequency: (e.frequency || 0) + 1 }
              : e
          ).concat(entity.frequency > 0 ? [] : [entity])
        )
      );

      const listCacheKey = entity.source === "task"
        ? TASK_LIST_CACHE_KEY
        : ACTIVITY_LIST_CACHE_KEY;

      queryClient.setQueryData(listCacheKey, (currentEntities = []) =>
        dedupeEntities(
          currentEntities.map((e) =>
            getEntityCacheKey(e) === getEntityCacheKey(entity)
              ? { ...e, frequency: (e.frequency || 0) + 1 }
              : e
          ).concat(entity.frequency > 0 ? [] : [entity])
        )
      );

      return entity;
    },
    [config.queryKey, normalizeEntity, queryClient, type]
  );

  const activities = queryClient.getQueryData(ACTIVITY_LIST_CACHE_KEY) ?? [];
  const tasks = queryClient.getQueryData(TASK_LIST_CACHE_KEY) ?? [];

  return {
    ...query,
    entities: query.data ?? [],
    activities,
    tasks,
    addEntityToCache,
  };
}
