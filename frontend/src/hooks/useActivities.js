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
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => updateActivity(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["activities"] });
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
