// src/hooks/useActivities.ts

import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { updateActivity, deleteActivity, fetchActivities, createActivity, logOfflineActivity } from "../api/activities";
import type { PlayerActivity } from "../types";


export function useActivities() {
  return useQuery({
    queryKey: ["activities"],
    queryFn: fetchActivities,
    staleTime: 30_000,
  });
}


export function useCreateActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createActivity,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}


export function useLogOfflineActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logOfflineActivity,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activities"] });
      // A task may have been auto-created (or its total time updated) by the log.
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}


export function useUpdateActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ activityId, data }: { activityId: number; data: Partial<PlayerActivity> }) => updateActivity(activityId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}

export function useChangeActivitySkill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ activityId, skillId }: { activityId: number; skillId: number }) =>
      updateActivity(activityId, { skill_id: skillId } as Partial<PlayerActivity>), // re-use your updateActivity API
    onSuccess: () => {
      // Refresh activities so the UI reflects the new skill
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}

export function useChangeActivityTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ activityId, taskId }: { activityId: number; taskId: number | null }) =>
      updateActivity(activityId, { task_id: taskId } as Partial<PlayerActivity>), // re-use your updateActivity API
    onSuccess: () => {
      // Refresh activities so the UI reflects the new task
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}

export function useDeleteActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteActivity,
    onMutate: async (activityId: number) => {
      await queryClient.cancelQueries({ queryKey: ["activities"] });

      const previousActivities = queryClient.getQueryData<PlayerActivity[]>(["activities"]);

      queryClient.setQueryData<PlayerActivity[]>(["activities"], (old = []) =>
        old.filter((activity) => activity.id !== activityId)
      );

      return { previousActivities };
    },
    // Rollback on error
    onError: (_err: unknown, _activityId: number, context: { previousActivities?: PlayerActivity[] } | undefined) => {
      if (context?.previousActivities) {
        queryClient.setQueryData(["activities"], context.previousActivities);
      }
    },
    // Ensure the cache is in sync with backend
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}
