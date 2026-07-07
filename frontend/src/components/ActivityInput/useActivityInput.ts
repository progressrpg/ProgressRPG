import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useGame } from "../../hooks/useGame";
import { useEntitySearchCache } from "../../hooks/useEntitySearchCache";
import { useDefaultActivityEntries } from "../../hooks/useDefaultActivityEntries";
import { useSupportFlow } from "../../hooks/useSupportFlow";
import type { PlayerActivity } from "../../types";
import { playLimitReachedSound, primeAudio } from "../../utils/sounds";

const WELCOME_MESSAGE_LAST_EVENT_KEY = "supportFlow_lastLoginEventAtShown";

interface SelectedEntity {
  name: string;
  id?: number | string | null;
  taskId?: number | null;
  source?: string;
}

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
  fetchPlayerAndCharacter,
  fetchCharacterCurrent,
  fetchActivities,
  isPremium,
  openActivityReward,
  setName,
}: {
  autoStopCompletion: ReturnType<typeof useGame>["activityTimer"]["autoStopCompletion"];
  clearAutoStopCompletion: ReturnType<typeof useGame>["activityTimer"]["clearAutoStopCompletion"];
  fetchPlayerAndCharacter: ReturnType<typeof useGame>["fetchPlayerAndCharacter"];
  fetchCharacterCurrent: ReturnType<typeof useGame>["fetchCharacterCurrent"];
  fetchActivities: ReturnType<typeof useGame>["fetchActivities"];
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

      try {
        await Promise.all([fetchPlayerAndCharacter(), fetchCharacterCurrent(), fetchActivities()]);
      } catch (err) {
        console.error("[ActivityInput] Failed to refresh after auto-stop:", err);
      }

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
    fetchPlayerAndCharacter,
    fetchActivities,
    fetchCharacterCurrent,
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

  const { currentActivity, status, stop, startActivity, elapsed, limitSeconds, autoStopCompletion, clearAutoStopCompletion } =
    activityTimer;

  const isPremium = Boolean(player?.is_premium);
  const queryClient = useQueryClient();
  const { addEntityToCache } = useEntitySearchCache("activity");
  const defaultEntries = useDefaultActivityEntries();

  const [name, setName] = useState("");

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
  const inputValue = isActive ? name || currentActivity?.name || "" : name;

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

  useAutoStopCompletionEffect({
    autoStopCompletion,
    clearAutoStopCompletion,
    fetchPlayerAndCharacter,
    fetchCharacterCurrent,
    fetchActivities,
    isPremium,
    openActivityReward,
    setName,
  });

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

      try {
        await Promise.all([
          fetchPlayerAndCharacter(),
          fetchCharacterCurrent(),
          fetchActivities(),
          completedTaskId ? queryClient.invalidateQueries({ queryKey: ["tasks"] }) : Promise.resolve(),
        ]);
      } catch (err) {
        console.error("[ActivityInput] Failed to refresh after stop:", err);
      }

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

    const nextName = name.trim();
    if (nextName) addEntityToCache(nextName);
    await startActivity({ text: nextName, limitSeconds: isPremium ? null : freeTimerLimitSeconds });
  }, [
    addEntityToCache,
    currentActivity?.name,
    currentActivity?.taskId,
    elapsed,
    fetchActivities,
    fetchCharacterCurrent,
    fetchPlayerAndCharacter,
    freeTimerLimitSeconds,
    isActive,
    isPremium,
    name,
    openActivityReward,
    queryClient,
    startActivity,
    stop,
  ]);

  const handleSelectActivity = useCallback(
    async (activity: SelectedEntity) => {
      setName(activity.name);
      addEntityToCache(activity as unknown as Partial<PlayerActivity>);
      await startActivity({
        text: activity.name,
        taskId: resolveSelectedTaskId(activity),
        limitSeconds: isPremium ? null : freeTimerLimitSeconds,
      });
    },
    [addEntityToCache, freeTimerLimitSeconds, isPremium, startActivity]
  );

  const handleCreateActivity = useCallback(
    async (activityName: string) => {
      setName(activityName);
      addEntityToCache(activityName);
      await startActivity({
        text: activityName,
        limitSeconds: isPremium ? null : freeTimerLimitSeconds,
      });
    },
    [addEntityToCache, freeTimerLimitSeconds, isPremium, startActivity]
  );

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

    try {
      await Promise.all([fetchPlayerAndCharacter(), fetchCharacterCurrent(), fetchActivities()]);
    } catch (err) {
      console.error("[ActivityInput] Failed to refresh after Task Support submit:", err);
    }

    openSupportMode();
  }, [
    currentActivity?.name,
    currentActivity?.text,
    fetchActivities,
    fetchCharacterCurrent,
    fetchPlayerAndCharacter,
    name,
    openSupportMode,
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
    const warningThresholdSeconds =
      typeof limitSeconds === "number" && limitSeconds > 0 ? limitSeconds * 0.9 : null;

    return (
      isActive &&
      typeof limitSeconds === "number" &&
      limitSeconds > 0 &&
      warningThresholdSeconds !== null &&
      elapsed >= warningThresholdSeconds &&
      elapsed < limitSeconds
    );
  }, [elapsed, isActive, limitSeconds]);

  return {
    name,
    setName,
    isActive,
    inputValue,
    minutes,
    seconds,
    formattedLimit,
    showAutoStopWarning,
    flowState,
    flowDispatch,
    handleConfirmActivity,
    handleToggle,
    handleSelectActivity,
    handleCreateActivity,
    submitAndOpenSupport,
    openSupportMode,
    isPremium,
    defaultEntries,
  };
}
