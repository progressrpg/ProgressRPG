// src/hooks/useOnboarding.js
import { useMemo, useState, useCallback } from 'react';
import { apiFetch } from "../utils/api";
import { useGame } from '../context/GameContext';

export default function useOnboarding() {
  const {
    player,
    loading,
    fetchPlayerAndCharacter,
  } = useGame();
  const [error, setError] = useState("");

  const completed = useMemo(() => {
    if (!player) return undefined;
    return Boolean(player.onboarding_completed);
  }, [player]);

  const completeOnboarding = useCallback(async () => {
    try {
      await apiFetch("/me/complete_onboarding/", {
        method: "POST",
      });

      await fetchPlayerAndCharacter?.();
      //console.log("player after fetching:", player);
      return true;
    } catch (err) {
      console.error("[Onboarding] Complete error:", err);
      setError(err?.message || "Failed to complete onboarding.");
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
