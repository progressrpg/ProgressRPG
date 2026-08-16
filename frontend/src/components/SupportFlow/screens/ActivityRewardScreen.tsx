// SupportFlow/screens/ActivityRewardScreen.tsx
import React, { useEffect, useRef, useState } from "react";
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { formatRewardDuration } from "../../../utils/formatUtils";
import { useTasks, useUpdateTask } from "../../../hooks/useTasks";
import { useGame } from "../../../hooks/useGame";
import RewardBreakdown from "./RewardBreakdown";
import styles from "../SupportFlowModal.module.scss";

const SUPPORT_COUNTDOWN_MS = 3000;

interface ActivityRewardScreenProps {
  activityName?: string | null;
  xpGained?: number | null;
  baseXp?: number | null;
  xpMultiplier?: number | null;
  taskXpMultiplier?: number | null;
  levelUps?: number[];
  isAutoStopped?: boolean;
  showUpgradePrompt?: boolean;
  elapsedSeconds?: number | null;
  taskId?: number | null;
  enableAutoSupportCountdown?: boolean;
  onContinue?: () => void;
  onSupport?: () => void;
}

export default function ActivityRewardScreen({
  activityName,
  xpGained,
  baseXp,
  xpMultiplier,
  taskXpMultiplier = null,
  levelUps = [],
  isAutoStopped = false,
  showUpgradePrompt = false,
  elapsedSeconds,
  taskId = null,
  enableAutoSupportCountdown = true,
  onContinue,
  onSupport,
}: ActivityRewardScreenProps) {
  const shouldEnableCountdown = Boolean(enableAutoSupportCountdown);
  const [remainingMs, setRemainingMs] = useState(SUPPORT_COUNTDOWN_MS);
  const [isCountdownPaused, setIsCountdownPaused] = useState(false);
  const hasAutoContinuedRef = useRef(false);

  const { fetchPlayerAndCharacter } = useGame();
  const { data: tasks = [] } = useTasks();
  const updateTask = useUpdateTask();
  const linkedTask = taskId != null ? tasks.find((t) => t.id === taskId) ?? null : null;
  const [isTaskComplete, setIsTaskComplete] = useState<boolean>(linkedTask?.is_complete ?? false);
  // Sync initial value once linkedTask loads (it may arrive after first render)
  const hasInitialisedTaskComplete = useRef(false);
  useEffect(() => {
    if (linkedTask && !hasInitialisedTaskComplete.current) {
      setIsTaskComplete(linkedTask.is_complete);
      hasInitialisedTaskComplete.current = true;
    }
  }, [linkedTask]);

  function handleToggleTaskComplete() {
    if (!linkedTask) return;
    const next = !isTaskComplete;
    setIsTaskComplete(next);
    updateTask.mutate(
      { id: linkedTask.id, data: { is_complete: next } },
      {
        onSuccess: (data) => {
          if (data.completion_xp_gained > 0) fetchPlayerAndCharacter();
        },
      }
    );
  }

  useEffect(() => {
    if (!shouldEnableCountdown || isCountdownPaused || hasAutoContinuedRef.current) {
      return undefined;
    }

    const intervalId = setInterval(() => {
      setRemainingMs((prev) => Math.max(0, prev - 100));
    }, 100);

    return () => clearInterval(intervalId);
  }, [isCountdownPaused, onSupport, shouldEnableCountdown]);

  useEffect(() => {
    if (!shouldEnableCountdown || hasAutoContinuedRef.current || remainingMs > 0) {
      return;
    }

    hasAutoContinuedRef.current = true;
    onSupport?.();
  }, [onSupport, remainingMs, shouldEnableCountdown]);

  const countdownSeconds = Math.max(1, Math.ceil(remainingMs / 1000));
  const continueButtonLabel = shouldEnableCountdown
    ? `Continue with support in ${countdownSeconds}..`
    : "Continue with support";
  const parsedBaseXp = Number(baseXp);
  const parsedMultiplier = Number(xpMultiplier);
  const hasRewardBreakdown =
    Number.isFinite(parsedBaseXp) &&
    parsedBaseXp >= 0 &&
    Number.isFinite(parsedMultiplier) &&
    parsedMultiplier > 0 &&
    Number.isFinite(Number(xpGained));
  const parsedTaskXpMultiplier = Number(taskXpMultiplier);
  const hasTaskBonus =
    Number.isFinite(parsedTaskXpMultiplier) && parsedTaskXpMultiplier > 1;
  // Infer premium component: combined / task (or combined if no task bonus).
  // Duplicated (not shared) with RewardBreakdown's own copy of this
  // calculation — it's only used here to gate the upgrade prompt, which is
  // specific to this modal screen, not the extracted breakdown display.
  const premiumMultiplier =
    hasRewardBreakdown && hasTaskBonus && parsedTaskXpMultiplier > 0
      ? parsedMultiplier / parsedTaskXpMultiplier
      : parsedMultiplier;
  const isLikelyPremiumUser = premiumMultiplier >= 2;
  const shouldShowUpgradePrompt = Boolean(showUpgradePrompt) && !isLikelyPremiumUser;
  const upgradeMessage = shouldShowUpgradePrompt
    ? isAutoStopped
      ? "Need more time? Upgrade to Premium for unlimited timer sessions."
      : "Want even more rewards? Upgrade to Premium for double XP on activities."
    : null;

  return (
    <div>
      <RewardBreakdown
        activityName={activityName}
        xpGained={xpGained}
        baseXp={baseXp}
        xpMultiplier={xpMultiplier}
        taskXpMultiplier={taskXpMultiplier}
        levelUps={levelUps}
        elapsedSeconds={elapsedSeconds}
      />

      {linkedTask && (
        <div className={styles.taskCompletionPanel}>
          <p className={styles.taskCompletionTitle}>Task: {linkedTask.name}</p>
          <div className={styles.taskCompletionRow}>
            <span className={styles.taskCompletionTime}>
              Total time: {formatRewardDuration(linkedTask.total_time)}
            </span>
            <label className={styles.taskCompletionCheck}>
              Completed task?
              <input
                type="checkbox"
                checked={isTaskComplete}
                onChange={handleToggleTaskComplete}
              />
            </label>
          </div>
          {(updateTask.data?.completion_xp_gained ?? 0) > 0 && (
            <p className={styles.taskCompletionXp}>
              +{updateTask.data!.completion_xp_gained} XP for completing the task!
            </p>
          )}
        </div>
      )}

      <div className={styles.actionRow}>
        <div
          className={`${styles.supportPanel} ${isCountdownPaused ? styles.supportPanelPaused : ""}`}
          onPointerEnter={shouldEnableCountdown ? () => setIsCountdownPaused(true) : undefined}
          onPointerLeave={shouldEnableCountdown ? () => setIsCountdownPaused(false) : undefined}
        >
          <div className={styles.supportPanelActions}>
            <ButtonFrame>
              <Button
                onClick={onSupport}
                className={shouldEnableCountdown ? styles.supportCountdownButton : undefined}
                style={
                  shouldEnableCountdown
                    ? { "--support-countdown-duration": `${SUPPORT_COUNTDOWN_MS}ms` } as React.CSSProperties
                    : undefined
                }
              >
                {continueButtonLabel}
              </Button>
            </ButtonFrame>
            <ButtonFrame>
              <Button variant="secondary" onClick={onContinue}>
                Back to timer
              </Button>
            </ButtonFrame>
          </div>
        </div>

        {shouldShowUpgradePrompt && (
          <div className={styles.upgradePanel}>
            {upgradeMessage && <p>{upgradeMessage}</p>}
            <ButtonFrame>
              <Button as="a" href="/upgrade" variant="secondary">Upgrade to Premium</Button>
            </ButtonFrame>
          </div>
        )}
      </div>
    </div>
  );
}
