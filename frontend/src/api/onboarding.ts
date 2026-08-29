// src/api/onboarding.ts
import { apiFetch } from "../utils/api";

export function completeOnboarding(): Promise<void> {
  return apiFetch<void>("/me/complete_onboarding/", {
    method: "POST",
  });
}
