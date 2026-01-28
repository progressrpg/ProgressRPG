// components/CharacterActivityCurrent/CharacterActivityCurrent.jsx
import { useEffect } from "react";
import { useGame } from "../../context/GameContext";
import styles from "./CharacterCurrentActivity.module.scss";

const fmtTime = (iso) =>
  iso
    ? new Date(iso).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

export default function CharacterCurrentActivity() {
  const {
    character,
    characterCurrentActivity,
    fetchCharacterCurrent,
  } = useGame();

  useEffect(() => {
    fetchCharacterCurrent();
  }, [fetchCharacterCurrent]);

  if (!character || !characterCurrentActivity) return null;

  const activityName =
    characterCurrentActivity.name?.trim().toLowerCase() ||
    characterCurrentActivity.kind;

  const startTime = fmtTime(characterCurrentActivity.started_at || characterCurrentActivity.scheduled_start);

  return (

    <div className={styles.line}>
      <p>
        <strong>{character.first_name}</strong> began{" "}
        <span className={styles.activity}>{activityName}</span>{" "}
        at <span className={styles.time}>{startTime}</span>
      </p>
      <p>
        ⚡ Online bonus active (+20% XP)
      </p>
    </div>

  );
}
