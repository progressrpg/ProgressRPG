// src/hooks/useOnboarding.ts

import { useMemo, useState, useCallback } from 'react';
import { completeOnboarding as completeOnboardingRequest } from "../api/onboarding";
import { useGame } from './useGame';

export default function useOnboarding() {
  const {
    player,
    loading,
    fetchPlayerAndCharacter,
  } = useGame();
  const [error, setError] = useState<string>("");

  const completed = useMemo((): boolean | undefined => {
    if (!player) return undefined;
    return Boolean(player.onboarding_completed);
  }, [player]);

  const completeOnboarding = useCallback(async (): Promise<boolean> => {
    try {
      await completeOnboardingRequest();

      await fetchPlayerAndCharacter?.();
      //console.log("player after fetching:", player);
      return true;
    } catch (err) {
      console.error("[Onboarding] Complete error:", err);
      const error = err as Error | null;
      setError(error?.message || "Failed to complete onboarding.");
      return false;
    }
  }, [fetchPlayerAndCharacter]);

  return {
    completed,
    completeOnboarding,
    loading,
    error,
  };
}
