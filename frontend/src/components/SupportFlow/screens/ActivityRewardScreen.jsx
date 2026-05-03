// SupportFlow/screens/ActivityRewardScreen.jsx
import { useEffect, useRef, useState } from "react";
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { formatDuration, formatRewardDuration } from "../../../utils/formatUtils.js";
import styles from "../SupportFlowModal.module.scss";

const SUPPORT_COUNTDOWN_MS = 3000;

export default function ActivityRewardScreen({
  activityName,
  xpGained,
  baseXp,
  xpMultiplier,
  levelUps = [],
  isAutoStopped = false,
  showUpgradePrompt = false,
  elapsedSeconds,
  enableAutoSupportCountdown = true,
  onContinue,
  onSupport,
}) {
  const shouldEnableCountdown = Boolean(enableAutoSupportCountdown);
  const [remainingMs, setRemainingMs] = useState(SUPPORT_COUNTDOWN_MS);
  const [isCountdownPaused, setIsCountdownPaused] = useState(false);
  const hasAutoContinuedRef = useRef(false);

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
  const hasActivityName = typeof activityName === "string" && activityName.trim();
  const parsedXp = Number(xpGained);
  const hasXp = Number.isFinite(parsedXp);
  const parsedBaseXp = Number(baseXp);
  const parsedMultiplier = Number(xpMultiplier);
  const hasRewardBreakdown =
    Number.isFinite(parsedBaseXp) &&
    parsedBaseXp >= 0 &&
    Number.isFinite(parsedMultiplier) &&
    parsedMultiplier > 0 &&
    hasXp;
  const parsedElapsedSeconds = Number(elapsedSeconds);
  const hasElapsedSeconds =
    Number.isFinite(parsedElapsedSeconds) && parsedElapsedSeconds >= 0;
  const formattedElapsed = hasElapsedSeconds
    ? formatRewardDuration(parsedElapsedSeconds)
    : null;
  const condensedElapsed = hasElapsedSeconds
    ? formatDuration(parsedElapsedSeconds)
    : null;
  const formattedMultiplier = hasRewardBreakdown
    ? Number.isInteger(parsedMultiplier)
      ? String(parsedMultiplier)
      : parsedMultiplier.toFixed(2).replace(/\.?0+$/, "")
    : null;
  const normalizedLevelUps = Array.isArray(levelUps)
    ? levelUps
        .map((level) => Number(level))
        .filter((level) => Number.isInteger(level) && level > 0)
    : [];
  const isLikelyPremiumUser = parsedMultiplier === 2;
  const shouldShowUpgradePrompt = Boolean(showUpgradePrompt) && !isLikelyPremiumUser;
  const upgradeMessage = shouldShowUpgradePrompt
    ? isAutoStopped
      ? "Need more time? Upgrade to Premium for unlimited timer sessions."
      : "Want even more rewards? Upgrade to Premium for double XP on activities."
    : null;
  const multiplierLines = [];
  let rewardSummaryLine = "Nice work ⚔️ You completed an activity.";

  if (formattedElapsed && hasActivityName) {
    rewardSummaryLine = `Nice work ⚔️ You spent ${formattedElapsed} on "${activityName.trim()}".`;
  } else if (hasActivityName) {
    rewardSummaryLine = `Nice work ⚔️ You completed "${activityName.trim()}".`;
  } else if (formattedElapsed) {
    rewardSummaryLine = `Nice work ⚔️ You spent ${formattedElapsed} focused.`;
  }

  if (hasRewardBreakdown && parsedMultiplier > 1) {
    if (parsedMultiplier === 2) {
      multiplierLines.push({ label: "Premium bonus", value: `x${formattedMultiplier}` });
    } else {
      multiplierLines.push({ label: "Activity XP", value: `x${formattedMultiplier}` });
    }
  }

  return (
    <div>
      {(hasElapsedSeconds || hasXp) && (
        <div className={styles.rewardBreakdown}>
          <p className={styles.rewardSummary}>{rewardSummaryLine}</p>
          {condensedElapsed && (
            <div className={styles.rewardBreakdownRow}>
              <span className={styles.rewardBreakdownLabel}>Time</span>
              <span className={styles.rewardBreakdownValue}>{condensedElapsed}</span>
            </div>
          )}
          {multiplierLines.map((line) => (
            <div className={styles.rewardBreakdownRow} key={line.label}>
              <span className={styles.rewardBreakdownLabel}>{line.label}</span>
              <span className={styles.rewardBreakdownValue}>{line.value}</span>
            </div>
          ))}
          {hasXp && (
            <div className={styles.rewardBreakdownRowPrimary}>
              <span className={styles.rewardBreakdownLabel}>Total XP gained</span>
              <span className={styles.rewardBreakdownValue}>+{parsedXp} XP</span>
            </div>
          )}
        </div>
      )}
      {!(hasElapsedSeconds || hasXp) && <p>{rewardSummaryLine}</p>}
      {normalizedLevelUps.map((level) => (
        <p key={level}>Level up! You reached level {level}.</p>
      ))}
      {!hasActivityName && hasXp && <p>You gained {parsedXp} XP!</p>}

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
                    ? { "--support-countdown-duration": `${SUPPORT_COUNTDOWN_MS}ms` }
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
