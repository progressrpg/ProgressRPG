import { useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchActivities } from "../api/activities";

const ENTITY_CONFIG = {
  activity: {
    queryKey: ["entity-search", "activity"],
    queryFn: fetchActivities,
  },
};

function normalizeEntityName(value) {
  return typeof value === "string" ? value.trim().replace(/\s+/g, " ") : "";
}

function getEntityNameKey(name) {
  return normalizeEntityName(name).toLowerCase();
}

function normalizeActivityEntity(activity) {
  const name = normalizeEntityName(activity?.name);
  if (!name) return null;

  return {
    id: activity?.id ?? `activity-${name.toLowerCase()}`,
    name,
    completedAt: activity?.completed_at ?? null,
    isOptimistic: Boolean(activity?.isOptimistic),
    frequency: activity?.frequency ?? 0,
  };
}

function getEntityNormalizer(type) {
  if (type === "activity") {
    return normalizeActivityEntity;
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
    const key = getEntityNameKey(entity.name);
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
      const normalizedEntities = Array.isArray(data)
        ? data.map(normalizeEntity).filter(Boolean)
        : [];

      return dedupeEntities(normalizedEntities);
    },
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: Number.POSITIVE_INFINITY,
    refetchOnWindowFocus: false,
  });

  const addEntityToCache = useCallback(
    (entityInput) => {
      const entity =
        typeof entityInput === "string"
          ? normalizeEntity({ name: entityInput, isOptimistic: true })
          : normalizeEntity(entityInput);

      if (!entity) {
        return null;
      }

      queryClient.setQueryData(config.queryKey, (currentEntities = []) =>
        dedupeEntities(
          currentEntities.map((e) =>
            e.name.toLowerCase() === entity.name.toLowerCase()
              ? { ...e, frequency: (e.frequency || 0) + 1 }
              : e
          ).concat(entity.frequency > 0 ? [] : [entity])
        )
      );

      return entity;
    },
    [config.queryKey, normalizeEntity, queryClient]
  );

  return {
    ...query,
    entities: query.data ?? [],
    addEntityToCache,
  };
}
