// src/hooks/useActivities.js

import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { updateActivity, deleteActivity, fetchActivities, createActivity } from "../api/activities";


export function useActivities() {
  return useQuery({
    queryKey: ["activities"],
    queryFn: fetchActivities,
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


export function useUpdateActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ activityId, data }) => updateActivity(activityId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}

export function useChangeActivitySkill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ activityId, skillId }) =>
      updateActivity(activityId, { skill_id: skillId }), // re-use your updateActivity API
    onSuccess: () => {
      // Refresh activities so the UI reflects the new skill
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}

export function useChangeActivityTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ activityId, taskId }) =>
      updateActivity(activityId, { task_id: taskId }), // re-use your updateActivity API
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
    onMutate: async (activityId) => {
      await queryClient.cancelQueries({ queryKey: ["activities"] });

      const previousActivities = queryClient.getQueryData(["activities"]);

      queryClient.setQueryData(["activities"], (old) =>
        old.filter((activity) => activity.id !== activityId)
      );

      return { previousActivities };
    },
    // Rollback on error
    onError: (err, activityId, context) => {
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
