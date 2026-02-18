// components/CharacterActivityCurrent/CharacterActivityCurrent.jsx
import { useEffect, useMemo, useState } from "react";
import { useGame } from "../../context/GameContext";
import styles from "./CharacterCurrentActivity.module.scss";

export default function CharacterCurrentActivity() {
  const {
    character,
    characterCurrentActivity,
    fetchCharacterCurrent,
    activityTimer,
  } = useGame();

  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    fetchCharacterCurrent();
  }, [fetchCharacterCurrent]);

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  const timeRemaining = useMemo(() => {
    const scheduledEnd = characterCurrentActivity?.scheduled_end;
    if (!scheduledEnd) return "";

    const scheduledEndMs = new Date(scheduledEnd).getTime();
    if (!Number.isFinite(scheduledEndMs)) return "";


    const remainingMs = scheduledEndMs - now;
    if (remainingMs <= 0) return "";

    const totalMinutes = Math.floor(remainingMs / 60000);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  }, [characterCurrentActivity, now]);

  if (!character || !characterCurrentActivity) return null;

  const activityName =
  characterCurrentActivity.name?.trim().toLowerCase() ||
  characterCurrentActivity.kind ||
  "an activity";

  const isActive = activityTimer?.status === "active";

  return (

    <div className={styles.line}>
      <p>
        <strong>{character.first_name}</strong> is{" "}
        <span className={styles.activity}>{activityName}</span>
        {timeRemaining && (
          <span className={styles.remaining}> ({timeRemaining})</span>
        )}
      </p>
      <p className={styles.bonus}>Player online: +20% XP</p>
      {isActive && (
        <p className={styles.bonusActive}>Player active: +50% XP</p>
      )}
    </div>

  );
}
