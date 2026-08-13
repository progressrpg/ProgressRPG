import { useCallback, useMemo, useState } from "react";

import { useLogOfflineActivity } from "../../hooks/useActivities";
import { useGame } from "../../hooks/useGame";
import type { SearchEntity } from "../EntitySearchInput/useEntitySearchInput";
import type { OfflineActivityLogResponse } from "../../types";

// Must match OFFLINE_XP_ELIGIBLE_BACKDATE_WINDOW in progression/services.py —
// duplicated here only for the client-side "will this earn XP" hint; the
// backend remains the authority on whether XP is actually awarded.
const XP_ELIGIBLE_BACKDATE_DAYS = 7;

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

function todayDateValue(): string {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function nowTimeValue(): string {
  const now = new Date();
  return `${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

function extractErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    try {
      const parsed = JSON.parse(error.message) as Record<string, unknown>;
      if (typeof parsed.message === "string") return parsed.message;

      const firstFieldError = Object.values(parsed).find(
        (value): value is string[] =>
          Array.isArray(value) && typeof value[0] === "string"
      );
      if (firstFieldError) return firstFieldError[0];
    } catch {
      // Not a JSON error body — fall back to the raw message below.
    }
    return error.message;
  }
  return "Something went wrong logging this activity. Please try again.";
}

export interface FieldErrors {
  task?: string;
  duration?: string;
  completedAt?: string;
}

export function useLogOfflineActivityForm(onLogged?: () => void) {
  const { player, fetchPlayerAndCharacter } = useGame();
  const isPremium = Boolean(player?.is_premium);
  const logOfflineActivity = useLogOfflineActivity();

  const [taskName, setTaskName] = useState("");
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [durationHours, setDurationHours] = useState("");
  const [durationMinutes, setDurationMinutes] = useState("");
  const [completionDate, setCompletionDate] = useState(todayDateValue);
  const [completionTime, setCompletionTime] = useState(nowTimeValue);
  // Fixed at mount: caps the native date picker so future dates can't be
  // selected at all, rather than allowing them and erroring afterwards.
  const [maxCompletionDate] = useState(todayDateValue);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<OfflineActivityLogResponse | null>(null);
  // Read once at mount (a lazy initializer, not a render-phase call) and
  // refreshed by the date/time change handlers below — those are event
  // handlers, where reading the clock is fine.
  const [nowMs, setNowMs] = useState(() => Date.now());

  const handleCompletionDateChange = useCallback((value: string) => {
    setCompletionDate(value);
    setNowMs(Date.now());
  }, []);

  const handleCompletionTimeChange = useCallback((value: string) => {
    setCompletionTime(value);
    setNowMs(Date.now());
  }, []);

  const handleTaskNameChange = useCallback((value: string) => {
    setTaskName(value);
    setSelectedTaskId(null);
  }, []);

  const handleTaskSelect = useCallback((entity: SearchEntity) => {
    setTaskName(entity.name);
    setSelectedTaskId(typeof entity.id === "number" ? entity.id : Number(entity.id));
  }, []);

  const totalDurationMinutes = useMemo(() => {
    const hours = Number(durationHours || 0);
    const minutes = Number(durationMinutes || 0);
    if (Number.isNaN(hours) || Number.isNaN(minutes)) return NaN;
    return hours * 60 + minutes;
  }, [durationHours, durationMinutes]);

  const completedAt = useMemo(() => {
    if (!completionDate || !completionTime) return null;
    const date = new Date(`${completionDate}T${completionTime}`);
    return Number.isNaN(date.getTime()) ? null : date;
  }, [completionDate, completionTime]);

  const eligibility = useMemo(() => {
    if (!completedAt) return null;

    if (!isPremium) {
      return {
        tone: "info" as const,
        message: "This will be recorded, but offline activities only earn XP for Premium accounts.",
      };
    }

    const ageDays = (nowMs - completedAt.getTime()) / (24 * 60 * 60 * 1000);
    if (ageDays > XP_ELIGIBLE_BACKDATE_DAYS) {
      return {
        tone: "warning" as const,
        message: `This is more than ${XP_ELIGIBLE_BACKDATE_DAYS} days old, so it will be recorded but won't earn XP.`,
      };
    }

    return {
      tone: "success" as const,
      message: "This activity is eligible for XP, subject to your daily logging limits.",
    };
  }, [completedAt, isPremium, nowMs]);

  const validate = useCallback((): FieldErrors => {
    const errors: FieldErrors = {};

    if (!taskName.trim()) {
      errors.task = "Enter or select a task.";
    }

    const hours = durationHours ? Number(durationHours) : 0;
    const minutes = durationMinutes ? Number(durationMinutes) : 0;
    if (Number.isNaN(hours) || hours < 0) {
      errors.duration = "Hours must be a positive number.";
    } else if (Number.isNaN(minutes) || minutes < 0 || minutes > 59) {
      errors.duration = "Minutes must be between 0 and 59.";
    } else if (totalDurationMinutes <= 0) {
      errors.duration = "Enter a duration greater than zero.";
    }

    if (!completionDate || !completionTime) {
      errors.completedAt = "Enter a completion date and time.";
    } else if (!completedAt) {
      errors.completedAt = "Enter a valid completion date and time.";
    } else if (completedAt.getTime() > Date.now()) {
      errors.completedAt = "Completion date/time can't be in the future.";
    }

    return errors;
  }, [
    completedAt,
    completionDate,
    completionTime,
    durationHours,
    durationMinutes,
    taskName,
    totalDurationMinutes,
  ]);

  const reset = useCallback(() => {
    setTaskName("");
    setSelectedTaskId(null);
    setDurationHours("");
    setDurationMinutes("");
    setCompletionDate(todayDateValue());
    setCompletionTime(nowTimeValue());
    setNowMs(Date.now());
    setFieldErrors({});
    setSubmitError(null);
    setResult(null);
  }, []);

  const handleSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setSubmitError(null);

      const errors = validate();
      setFieldErrors(errors);
      if (Object.keys(errors).length > 0 || !completedAt) return;

      const durationSeconds = Math.round(totalDurationMinutes * 60);
      const startedAt = new Date(completedAt.getTime() - durationSeconds * 1000);

      logOfflineActivity.mutate(
        {
          ...(selectedTaskId ? { task: selectedTaskId } : { name: taskName.trim() }),
          started_at: startedAt.toISOString(),
          completed_at: completedAt.toISOString(),
        },
        {
          onSuccess: (data) => {
            setResult(data);
            if (data.xp_gained > 0) fetchPlayerAndCharacter();
            onLogged?.();
          },
          onError: (error) => setSubmitError(extractErrorMessage(error)),
        }
      );
    },
    [
      completedAt,
      fetchPlayerAndCharacter,
      logOfflineActivity,
      onLogged,
      selectedTaskId,
      taskName,
      totalDurationMinutes,
      validate,
    ]
  );

  return {
    taskName,
    handleTaskNameChange,
    handleTaskSelect,
    durationHours,
    setDurationHours,
    durationMinutes,
    setDurationMinutes,
    totalDurationMinutes,
    completionDate,
    handleCompletionDateChange,
    completionTime,
    handleCompletionTimeChange,
    maxCompletionDate,
    fieldErrors,
    submitError,
    result,
    eligibility,
    isSubmitting: logOfflineActivity.isPending,
    handleSubmit,
    reset,
  };
}
