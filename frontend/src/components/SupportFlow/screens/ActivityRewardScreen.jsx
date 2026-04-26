// SupportFlow/screens/ActivityRewardScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { formatDuration } from "../../../../utils/formatUtils.js";
import styles from "../SupportFlowModal.module.scss";

function formatRewardDuration(durationSeconds) {
  const totalSeconds = Math.max(0, Math.floor(durationSeconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    if (minutes > 0) {
      return `${hours} hour${hours === 1 ? "" : "s"} ${minutes} minute${minutes === 1 ? "" : "s"}`;
    }
    return `${hours} hour${hours === 1 ? "" : "s"}`;
  }

  if (minutes > 0) {
    if (seconds > 0) {
      return `${minutes} minute${minutes === 1 ? "" : "s"} ${seconds} second${seconds === 1 ? "" : "s"}`;
    }
    return `${minutes} minute${minutes === 1 ? "" : "s"}`;
  }

  return `${seconds} second${seconds === 1 ? "" : "s"}`;
}

export default function ActivityRewardScreen({
  activityName,
  xpGained,
  baseXp,
  xpMultiplier,
  levelUps = [],
  elapsedSeconds,
  onContinue,
  onSupport,
}) {
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
  const multiplierLines = [];

  if (hasRewardBreakdown && parsedMultiplier > 1) {
    if (parsedMultiplier === 2) {
      multiplierLines.push({ label: "Premium", value: `x${formattedMultiplier}` });
    } else {
      multiplierLines.push({ label: "Activity XP", value: `x${formattedMultiplier}` });
    }
  }

  return (
    <div>
      <p>Great work! 🎉 You completed an activity.</p>
      {formattedElapsed && hasActivityName && (
        <p>You spent {formattedElapsed} on "{activityName.trim()}".</p>
      )}
      {(hasElapsedSeconds || hasXp) && (
        <div className={styles.rewardBreakdown}>
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
            <div className={styles.rewardBreakdownRow}>
              <span className={styles.rewardBreakdownLabel}>Total XP gained</span>
              <span className={styles.rewardBreakdownValue}>{parsedXp} XP</span>
            </div>
          )}
        </div>
      )}
      {normalizedLevelUps.map((level) => (
        <p key={level}>Level up! You reached level {level}.</p>
      ))}
      {!hasActivityName && hasXp && <p>You gained {parsedXp} XP!</p>}
      <ButtonFrame>
        <Button onClick={onContinue}>Return to timer</Button>
        <Button onClick={onSupport}>Get support</Button>
      </ButtonFrame>
    </div>
  );
}
