import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchPreferences, updatePreferences } from "../../api/preferences";
import type { UserPreferencesResponse } from "../../types/api";

const PREFERENCES_QUERY_KEY = ["preferences"];

export function usePreferencesTab() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery<UserPreferencesResponse>({
    queryKey: PREFERENCES_QUERY_KEY,
    queryFn: fetchPreferences,
  });

  const updateMutation = useMutation({
    mutationFn: updatePreferences,
    onSuccess: (response) => {
      queryClient.setQueryData(PREFERENCES_QUERY_KEY, response);
    },
  });

  const handleToggle = (key: string, value: boolean) => {
    updateMutation.mutate({ [key]: value });
  };

  return {
    preferences: data?.preferences ?? [],
    isLoading,
    isError,
    handleToggle,
    pendingKey: updateMutation.isPending
      ? Object.keys(updateMutation.variables ?? {})[0]
      : null,
  };
}
