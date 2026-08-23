import { useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { useAuth } from "../../context/AuthContext";
import { fetchTimezoneChoices, updateUserSettings } from "../../api/user";

const TIMEZONE_CHOICES_QUERY_KEY = ["timezoneChoices"];

/** Best-effort browser timezone detection - unsupported/sandboxed
 * environments can throw or return an empty string, in which case there's
 * nothing to suggest and the picker just falls back to manual selection. */
function detectBrowserTimezone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}

export function useTimezonePreference() {
  const { user, setUser } = useAuth();

  const { data, isLoading, isError } = useQuery({
    queryKey: TIMEZONE_CHOICES_QUERY_KEY,
    queryFn: fetchTimezoneChoices,
    // Reference data (IANA zone names) - doesn't change during a session.
    staleTime: 60 * 60 * 1000,
  });

  const detectedTimezone = useMemo(() => detectBrowserTimezone(), []);

  const updateMutation = useMutation({
    mutationFn: updateUserSettings,
    onSuccess: (updatedUser) => {
      setUser(updatedUser);
    },
  });

  const currentTimezone = user?.timezone ?? "UTC";

  const handleTimezoneChange = (timezone: string) => {
    if (!timezone || timezone === currentTimezone) return;
    updateMutation.mutate({ timezone });
  };

  // Offered as a hint the user acts on, never applied automatically - a
  // returning user's saved timezone (e.g. set at signup, or deliberately
  // different from wherever they're currently browsing from) shouldn't be
  // silently overwritten by whatever this device reports today.
  const showDetectedTimezoneHint =
    !!detectedTimezone && detectedTimezone !== currentTimezone;

  return {
    timezones: data?.timezones ?? [],
    timezonesLoading: isLoading,
    timezonesError: isError,
    currentTimezone,
    detectedTimezone,
    showDetectedTimezoneHint,
    handleTimezoneChange,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.isError,
  };
}
