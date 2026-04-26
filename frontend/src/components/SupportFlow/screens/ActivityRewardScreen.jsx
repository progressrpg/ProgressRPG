// SupportFlow/screens/ActivityRewardScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { formatDuration } from "../../../../utils/formatUtils.js";

export default function ActivityRewardScreen({
  activityName,
  xpGained,
  elapsedSeconds,
  onContinue,
  onSupport,
}) {
  const hasActivityName = typeof activityName === "string" && activityName.trim();
  const parsedXp = Number(xpGained);
  const hasXp = Number.isFinite(parsedXp);
  const parsedElapsedSeconds = Number(elapsedSeconds);
  const hasElapsedSeconds =
    Number.isFinite(parsedElapsedSeconds) && parsedElapsedSeconds >= 0;
  const formattedElapsed = hasElapsedSeconds
    ? formatDuration(parsedElapsedSeconds)
    : null;

  return (
    <div>
      <p>Great work! 🎉 You completed an activity.</p>
      {hasActivityName && hasXp && (
        <p>You completed "{activityName.trim()}" and gained {parsedXp} XP.</p>
      )}
      {hasActivityName && !hasXp && (
        <p>You completed {activityName.trim()}.</p>
      )}
      {!hasActivityName && hasXp && <p>You gained {parsedXp} XP.</p>}
      {formattedElapsed && <p>You spent {formattedElapsed} on this activity.</p>}
      <ButtonFrame>
        <Button onClick={onContinue}>Close window, use timer</Button>
        <Button onClick={onSupport}>Get support</Button>
      </ButtonFrame>
    </div>
  );
}
