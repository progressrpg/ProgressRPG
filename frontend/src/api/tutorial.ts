// src/api/tutorial.ts
import type { PaginatedResponse, TutorialStep } from "../types";
import { apiFetch } from "../utils/api";

export function fetchTutorialSteps(): Promise<PaginatedResponse<TutorialStep> | TutorialStep[]> {
  return apiFetch<PaginatedResponse<TutorialStep> | TutorialStep[]>("/tutorial-steps/");
}

export function markTutorialStepsSeen(stepIds: number[]): Promise<void> {
  return apiFetch<void>("/me/mark_tutorial_steps_seen/", {
    method: "POST",
    body: JSON.stringify({ step_ids: stepIds }),
  });
}
