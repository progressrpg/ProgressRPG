import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useGame } from "../../hooks/useGame";
import { useEntitySearchCache } from "../../hooks/useEntitySearchCache";
import { useSupportFlow } from "../../hooks/useSupportFlow";
import { TODAY_POINTS_QUERY_KEY } from "../../hooks/usePlayer";
import type { PlayerActivity } from "../../types";
import { playLimitReachedSound, primeAudio } from "../../utils/sounds";

const WELCOME_MESSAGE_LAST_EVENT_KEY = "supportFlow_lastLoginEventAtShown";

interface SelectedEntity {
  name: string;
  id?: number | string | null;
  taskId?: number | null;
  source?: string;
}

type CacheEntry = string | (Partial<PlayerActivity> & { isOptimistic?: boolean; frequency?: number });

function resolveSelectedTaskId(entity: SelectedEntity): number | null {
  if (entity?.source !== "task") return null;

  if (entity?.taskId !== null && entity?.taskId !== undefined) {
    return entity.taskId;
  }

  if (typeof entity?.id === "number") {
    return entity.id;
  }

  if (typeof entity?.id === "string" && /^\d+$/.test(entity.id)) {
    return parseInt(entity.id, 10);
  }

  return null;
}

function parseCompletionResponse(completion: Awaited<ReturnType<ReturnType<typeof useGame>["activityTimer"]["stop"]>>, fallbackElapsed: number) {
  const completionRaw = completion as Record<string, unknown> | null;

  return {
    xpGained: completionRaw?.xp_gained != null ? Number(completionRaw.xp_gained) : null,
    baseXp: completionRaw?.base_xp != null ? Number(completionRaw.base_xp) : null,
    xpMultiplier: completionRaw?.xp_multiplier != null ? Number(completionRaw.xp_multiplier) : null,
    taskXpMultiplier:
      completionRaw?.task_xp_multiplier != null ? Number(completionRaw.task_xp_multiplier) : null,
    levelUps: Array.isArray(completionRaw?.level_ups) ? (completionRaw.level_ups as number[]) : [],
    elapsedSeconds:
      completionRaw?.duration_seconds != null ? Number(completionRaw.duration_seconds) : fallbackElapsed,
  };
}

function useWelcomeMessageEffect({
  loginState,
  loginStreak,
  loginEventAt,
  loginRewardXp,
  openWelcomeMessage,
}: {
  loginState: string;
  loginStreak: number;
  loginEventAt: string | null;
  loginRewardXp: number;
  openWelcomeMessage: (args: {
    loginState: string;
    loginStreak: number;
    loginRewardXp: number;
  }) => void;
}) {
  useEffect(() => {
    if (loginState === "none" || !loginEventAt) return;

    let lastShownEventAt: string | null = null;
    try {
      lastShownEventAt = sessionStorage.getItem(WELCOME_MESSAGE_LAST_EVENT_KEY);
    } catch {
      // If sessionStorage is unavailable, fall back to opening the modal.
    }

    if (lastShownEventAt === loginEventAt) return;

    openWelcomeMessage({ loginState, loginStreak, loginRewardXp });

    try {
      sessionStorage.setItem(WELCOME_MESSAGE_LAST_EVENT_KEY, loginEventAt);
    } catch {
      // Ignore storage failures and keep app flow functional.
    }
  }, [loginState, loginStreak, loginEventAt, loginRewardXp, openWelcomeMessage]);
}

function useAutoStopCompletionEffect({
  autoStopCompletion,
  clearAutoStopCompletion,
  refreshAfterActivityChange,
  isPremium,
  openActivityReward,
  setName,
}: {
  autoStopCompletion: ReturnType<typeof useGame>["activityTimer"]["autoStopCompletion"];
  clearAutoStopCompletion: ReturnType<typeof useGame>["activityTimer"]["clearAutoStopCompletion"];
  refreshAfterActivityChange: (completedTaskId?: number | null) => Promise<void>;
  isPremium: boolean;
  openActivityReward: ReturnType<typeof useSupportFlow>["openActivityReward"];
  setName: (value: string) => void;
}) {
  useEffect(() => {
    if (!autoStopCompletion) return;

    let cancelled = false;
    const completion = autoStopCompletion;

    async function handleAutoStopCompletion() {
      setName("");
      await refreshAfterActivityChange();

      if (cancelled) return;

      playLimitReachedSound();

      const isFreeLimitAutoStop = completion.stopReason === "free_limit";

      openActivityReward({
        xpGained: completion.xpGained,
        baseXp: completion.baseXp,
        xpMultiplier: completion.xpMultiplier,
        taskXpMultiplier: completion.taskXpMultiplier,
        levelUps: completion.levelUps,
        isAutoStopped: true,
        showUpgradePrompt: !isPremium && isFreeLimitAutoStop,
        activityName: completion.activityName,
        elapsedSeconds: completion.elapsedSeconds,
      });
      clearAutoStopCompletion();
    }

    handleAutoStopCompletion();

    return () => {
      cancelled = true;
    };
  }, [
    autoStopCompletion,
    clearAutoStopCompletion,
    refreshAfterActivityChange,
    isPremium,
    openActivityReward,
    setName,
  ]);
}

export function useActivityInput() {
  const {
    activityTimer,
    fetchPlayerAndCharacter,
    fetchCharacterCurrent,
    fetchActivities,
    loginState,
    loginStreak,
    loginEventAt,
    loginRewardXp,
    player,
    freeTimerLimitSeconds,
  } = useGame();

  const { currentActivity, status, stop, startActivity, labelActivity, elapsed, limitSeconds, autoStopCompletion, clearAutoStopCompletion } =
    activityTimer;

  const isPremium = Boolean(player?.is_premium);
  const queryClient = useQueryClient();
  const { addEntityToCache } = useEntitySearchCache("activity");

  const [name, setName] = useState("");
  const [isEditingLabel, setIsEditingLabel] = useState(false);

  // Escape-to-cancel calls `.blur()` synchronously (to move focus off the
  // input immediately), but that fires before React flushes isEditingLabel's
  // state update — so the blur handler's closure still sees the pre-cancel
  // state and would wrongly treat the cancel as a commit. This flag records
  // "the last exit from edit mode was a cancel" so the blur handler can
  // distinguish it, without relying on state-update timing.
  const justCancelledLabelEditRef = useRef(false);

  const {
    openWelcomeMessage,
    openActivityReward,
    openSupportMode,
    flowState,
    flowDispatch,
    handleConfirmActivity,
  } = useSupportFlow({
    onStartActivity: async ({ activityText, durationSeconds, taskId }) => {
      const parsedDuration = Number(durationSeconds);
      const hasCustomDuration = Number.isFinite(parsedDuration) && parsedDuration > 0;

      let resolvedLimitSeconds: number | null = null;
      let limitReason: string | null = null;

      if (isPremium) {
        resolvedLimitSeconds = hasCustomDuration ? parsedDuration : null;
      } else if (!hasCustomDuration) {
        resolvedLimitSeconds = freeTimerLimitSeconds;
        limitReason = "free_limit";
      } else if (parsedDuration > freeTimerLimitSeconds) {
        resolvedLimitSeconds = freeTimerLimitSeconds;
        limitReason = "free_limit";
      } else {
        resolvedLimitSeconds = parsedDuration;
        limitReason = "preset_limit";
      }

      await startActivity({ text: activityText, limitSeconds: resolvedLimitSeconds, limitReason, taskId });
    },
  });

  const isActive = status === "active";
  // While actively editing (click-to-edit), `name` is the single source of
  // truth — including when the user has deleted it down to "". Falling back
  // to `currentActivity?.name` unconditionally here meant selecting all text
  // in the input and pressing Backspace/Delete would visibly "undo" itself:
  // `name` became "", so this fell back to the still-uncommitted old name.
  // Outside of active editing, the fallback is still needed (e.g. showing
  // the labelled activity's name before edit mode's own state has caught up).
  const inputValue = isActive ? (isEditingLabel ? name : name || currentActivity?.name || "") : name;
  const isUnlabelled = isActive && !(currentActivity?.name ?? currentActivity?.text ?? "").trim();

  useWelcomeMessageEffect({
    loginState,
    loginStreak,
    loginEventAt,
    loginRewardXp,
    openWelcomeMessage,
  });

  useEffect(() => {
    if (isActive) {
      (document.activeElement as HTMLElement | null)?.blur();
    }
  }, [isActive]);

  // Shared by the manual stop, the "submit & open support" stop, and the
  // auto-stop effect — all three stop or complete an activity and then need
  // the same player/character/activity data refreshed before showing a
  // reward or continuing the flow.
  const refreshAfterActivityChange = useCallback(
    async (completedTaskId: number | null = null) => {
      try {
        await Promise.all([
          fetchPlayerAndCharacter(),
          fetchCharacterCurrent(),
          fetchActivities(),
          queryClient.invalidateQueries({ queryKey: TODAY_POINTS_QUERY_KEY }),
          completedTaskId ? queryClient.invalidateQueries({ queryKey: ["tasks"] }) : Promise.resolve(),
        ]);
      } catch (err) {
        console.error("[ActivityInput] Failed to refresh activity state:", err);
      }
    },
    [fetchActivities, fetchCharacterCurrent, fetchPlayerAndCharacter, queryClient],
  );

  useAutoStopCompletionEffect({
    autoStopCompletion,
    clearAutoStopCompletion,
    refreshAfterActivityChange,
    isPremium,
    openActivityReward,
    setName,
  });

  // Starts a brand-new timer (no timer currently running). Shared by every
  // "not active" branch below — selecting a suggestion, creating a new
  // entry, submitting free text, or the blank-start button.
  const startNewActivity = useCallback(
    async (text: string, options?: { taskId?: number | null; cacheEntry?: CacheEntry; allowBlank?: boolean }) => {
      setName(text);
      if (options?.cacheEntry !== undefined) addEntityToCache(options.cacheEntry);

      const payload: Parameters<typeof startActivity>[0] = {
        text,
        limitSeconds: isPremium ? null : freeTimerLimitSeconds,
      };
      if (options?.taskId !== undefined) payload.taskId = options.taskId;
      if (options?.allowBlank !== undefined) payload.allowBlank = options.allowBlank;

      await startActivity(payload);
    },
    [addEntityToCache, freeTimerLimitSeconds, isPremium, startActivity],
  );

  // Relabels the currently-running timer. Shared by the unified select/submit
  // handlers' "already active" branch and by click-to-edit's commit path.
  const labelRunningActivity = useCallback(
    async (label: string, taskId: number | null, cacheEntry?: CacheEntry) => {
      setName(label);
      if (cacheEntry !== undefined) addEntityToCache(cacheEntry);
      await labelActivity(label, taskId);
      setIsEditingLabel(false);
    },
    [addEntityToCache, labelActivity],
  );

  const handleToggle = useCallback(async () => {
    primeAudio();

    if (isActive) {
      const completedActivityName = (name || currentActivity?.name || "").trim();
      const completedTaskId = currentActivity?.taskId ?? null;
      const localElapsed = elapsed;

      let completion: Awaited<ReturnType<typeof stop>> = null;
      try {
        completion = await stop({ activityName: completedActivityName });
      } catch (err) {
        console.error("[ActivityInput] Failed to stop timer:", err);
      }

      const {
        xpGained,
        baseXp,
        xpMultiplier,
        taskXpMultiplier,
        levelUps,
        elapsedSeconds,
      } = parseCompletionResponse(completion, localElapsed);

      setName("");
      await refreshAfterActivityChange(completedTaskId);

      playLimitReachedSound();
      openActivityReward({
        xpGained,
        baseXp,
        xpMultiplier,
        taskXpMultiplier,
        levelUps,
        isAutoStopped: false,
        showUpgradePrompt: !isPremium,
        activityName: completedActivityName || null,
        elapsedSeconds,
        taskId: completedTaskId,
      });
      return;
    }

    if (!name.trim()) return;
    await startNewActivity(name.trim(), { cacheEntry: name.trim() });
  }, [
    currentActivity?.name,
    currentActivity?.taskId,
    elapsed,
    isActive,
    isPremium,
    name,
    openActivityReward,
    refreshAfterActivityChange,
    startNewActivity,
    stop,
  ]);

  const handleBlankStart = useCallback(async () => {
    primeAudio();
    await startNewActivity("", { allowBlank: true });
  }, [startNewActivity]);

  const handleSelectActivity = useCallback(
    async (activity: SelectedEntity) => {
      await startNewActivity(activity.name, {
        taskId: resolveSelectedTaskId(activity),
        cacheEntry: activity as unknown as CacheEntry,
      });
    },
    [startNewActivity],
  );

  const handleCreateActivity = useCallback(
    async (activityName: string) => {
      await startNewActivity(activityName, { cacheEntry: activityName });
    },
    [startNewActivity],
  );

  // Selecting a list item: starts a timer if none is running, otherwise
  // attaches (or re-attaches) the selected label to the running timer —
  // covers both unlabelled->labelled and relabelling an already-labelled
  // timer, and is also what click-to-edit's blur/select path uses.
  const handleUnifiedSelect = useCallback(
    async (activity: SelectedEntity) => {
      if (!isActive) {
        await handleSelectActivity(activity);
        return;
      }

      await labelRunningActivity(activity.name, resolveSelectedTaskId(activity), activity as unknown as CacheEntry);
    },
    [handleSelectActivity, isActive, labelRunningActivity],
  );

  // Submitting free text: starts a timer if none is running, otherwise
  // relabels the running timer (including clearing the label if blank —
  // see handleLabelBlur).
  const handleUnifiedSubmit = useCallback(
    async (activityName: string) => {
      const trimmedName = activityName.trim();

      if (!isActive) {
        if (!trimmedName) return;
        await handleCreateActivity(trimmedName);
        return;
      }

      await labelRunningActivity(trimmedName, null, trimmedName ? trimmedName : undefined);
    },
    [handleCreateActivity, isActive, labelRunningActivity],
  );

  // Click-to-edit: clicking the running-labelled activity name pre-fills
  // the input with the current name and drops into the unlabelled layout.
  const startEditingLabel = useCallback(() => {
    setName(currentActivity?.name ?? currentActivity?.text ?? "");
    setIsEditingLabel(true);
  }, [currentActivity?.name, currentActivity?.text]);

  const handleLabelBlur = useCallback(async () => {
    await handleUnifiedSubmit(name);
    setIsEditingLabel(false);
  }, [handleUnifiedSubmit, name]);

  // Escape discards the edit — no labelActivity call, name reverts to
  // whatever the timer is currently actually labelled.
  const handleLabelCancel = useCallback(() => {
    justCancelledLabelEditRef.current = true;
    setName(currentActivity?.name ?? currentActivity?.text ?? "");
    setIsEditingLabel(false);
  }, [currentActivity?.name, currentActivity?.text]);

  // Consumed by the wrapper's blur handler to tell a genuine commit-blur
  // apart from the blur that Escape-cancel triggers synchronously.
  const consumeJustCancelledLabelEdit = useCallback(() => {
    if (!justCancelledLabelEditRef.current) return false;
    justCancelledLabelEditRef.current = false;
    return true;
  }, []);

  // Called when user confirms the "submit active timer?" AlertDialog in ActivityInput.
  const submitAndOpenSupport = useCallback(async () => {
    const completedActivityName = (name || currentActivity?.name || currentActivity?.text || "").trim();

    try {
      await stop({ activityName: completedActivityName });
    } catch (err) {
      console.error("[ActivityInput] Failed to submit active timer before Task Support:", err);
      return;
    }

    setName("");
    await refreshAfterActivityChange();

    openSupportMode();
  }, [
    currentActivity?.name,
    currentActivity?.text,
    name,
    openSupportMode,
    refreshAfterActivityChange,
    stop,
  ]);

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  const formattedLimit = useMemo(() => {
    if (typeof limitSeconds !== "number" || limitSeconds <= 0) {
      return null;
    }

    return `${Math.floor(limitSeconds / 60)}:${(limitSeconds % 60).toString().padStart(2, "0")}`;
  }, [limitSeconds]);

  const showAutoStopWarning = useMemo(() => {
    if (typeof limitSeconds !== "number" || limitSeconds <= 0) return false;

    const warningThresholdSeconds = limitSeconds * 0.9;
    return isActive && elapsed >= warningThresholdSeconds && elapsed < limitSeconds;
  }, [elapsed, isActive, limitSeconds]);

  return {
    name,
    setName,
    isActive,
    isUnlabelled,
    isEditingLabel,
    inputValue,
    minutes,
    seconds,
    formattedLimit,
    showAutoStopWarning,
    flowState,
    flowDispatch,
    handleConfirmActivity,
    handleToggle,
    handleBlankStart,
    handleSelectActivity,
    handleCreateActivity,
    handleUnifiedSelect,
    handleUnifiedSubmit,
    startEditingLabel,
    handleLabelBlur,
    handleLabelCancel,
    consumeJustCancelledLabelEdit,
    submitAndOpenSupport,
    openSupportMode,
    isPremium,
  };
}
