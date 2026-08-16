// SupportFlow/screens/RewardBreakdown.tsx
// Pure presentational reward-breakdown display: summary line, time, XP
// multipliers, total XP, and level-ups. No hooks, no fetching, no
// modal-specific styling assumptions — shared by ActivityRewardScreen (the
// SupportFlow modal) and the unified timer's Results state.
import { formatDuration, formatRewardDuration } from "../../../utils/formatUtils";
import styles from "./RewardBreakdown.module.scss";

interface RewardBreakdownProps {
  activityName?: string | null;
  xpGained?: number | null;
  baseXp?: number | null;
  xpMultiplier?: number | null;
  taskXpMultiplier?: number | null;
  levelUps?: number[];
  elapsedSeconds?: number | null;
}

function fmtMult(m: number): string {
  return Number.isInteger(m) ? String(m) : m.toFixed(2).replace(/\.?0+$/, "");
}

export default function RewardBreakdown({
  activityName,
  xpGained,
  baseXp,
  xpMultiplier,
  taskXpMultiplier = null,
  levelUps = [],
  elapsedSeconds,
}: RewardBreakdownProps) {
  const hasActivityName = typeof activityName === "string" && Boolean(activityName.trim());
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
  const parsedTaskXpMultiplier = Number(taskXpMultiplier);
  const hasTaskBonus =
    Number.isFinite(parsedTaskXpMultiplier) && parsedTaskXpMultiplier > 1;
  // Infer premium component: combined / task (or combined if no task bonus)
  const premiumMultiplier =
    hasRewardBreakdown && hasTaskBonus && parsedTaskXpMultiplier > 0
      ? parsedMultiplier / parsedTaskXpMultiplier
      : parsedMultiplier;

  const normalizedLevelUps = Array.isArray(levelUps)
    ? levelUps
        .map((level) => Number(level))
        .filter((level) => Number.isInteger(level) && level > 0)
    : [];

  const multiplierLines: Array<{ label: string; value: string }> = [];
  let rewardSummaryLine = "Nice work ⚔️ You completed an activity.";

  if (formattedElapsed && hasActivityName) {
    rewardSummaryLine = `Nice work ⚔️ You spent ${formattedElapsed} on "${activityName!.trim()}".`;
  } else if (hasActivityName) {
    rewardSummaryLine = `Nice work ⚔️ You completed "${activityName!.trim()}".`;
  } else if (formattedElapsed) {
    rewardSummaryLine = `Nice work ⚔️ You spent ${formattedElapsed} focused.`;
  }

  if (hasRewardBreakdown) {
    if (premiumMultiplier > 1) {
      multiplierLines.push({ label: "Premium bonus", value: `x${fmtMult(premiumMultiplier)}` });
    }
    if (hasTaskBonus) {
      multiplierLines.push({ label: "Task bonus", value: `x${fmtMult(parsedTaskXpMultiplier)}` });
    }
  }

  return (
    <>
      {hasElapsedSeconds || hasXp ? (
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
      ) : (
        <p>{rewardSummaryLine}</p>
      )}
      {normalizedLevelUps.map((level) => (
        <p key={level}>Level up! You reached level {level}.</p>
      ))}
      {!hasActivityName && hasXp && <p>You gained {parsedXp} XP!</p>}
    </>
  );
}
