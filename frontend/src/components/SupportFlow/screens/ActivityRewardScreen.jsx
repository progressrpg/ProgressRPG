// SupportFlow/screens/ActivityRewardScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";

export default function ActivityRewardScreen({ activityName, xpGained, onContinue, onSupport }) {
  const hasActivityName = typeof activityName === "string" && activityName.trim();
  const parsedXp = Number(xpGained);
  const hasXp = Number.isFinite(parsedXp);

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
      <ButtonFrame>
        <Button onClick={onContinue}>Close window, use timer</Button>
        <Button onClick={onSupport}>Get support</Button>
      </ButtonFrame>
    </div>
  );
}
