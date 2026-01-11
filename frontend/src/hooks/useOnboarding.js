// src/hooks/useOnboarding.js
import { useEffect, useState, useCallback } from 'react';
import { apiFetch } from '../../utils/api';

export default function useOnboarding() {
  //console.log('useOnboarding render');
  const [step, setStep] = useState(undefined);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  // Load current onboarding step on mount
  const refresh = useCallback(async () => {
      setLoading(true);
      try {
        const data = await apiFetch('/me/profile/');
        setStep(data.onboarding_step);
        setError('');
        return data;
      } catch (err) {
        console.error('[Onboarding] Status error:', err);
        setError('Failed to fetch onboarding status.');
      } finally {
        setLoading(false);
      }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);


  const updateOnboarding = useCallback(async (patch) => {
    try {
      const data = await apiFetch('/me/profile/', {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      if (typeof data.onboarding_step === "number") {
        setStep(data.onboarding_step);
      }
      setError("");
      return data;
    } catch (err) {
      console.error("[Onboarding] Onboarding update error:", err);
      setError(err?.message || "Failed to update onboarding.");
      return null;
    }
  }, []);

  const setOnboardingStep = useCallback(
    async (nextStep) => updateOnboarding({ onboarding_step: nextStep }),
    [updateOnboarding]
  );

  return {
    step,
    updateOnboarding,
    setOnboardingStep,
    refresh,
    loading,
    error,
  };
}
