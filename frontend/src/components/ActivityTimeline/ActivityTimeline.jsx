import { useMemo, useEffect } from "react";
import { useGame } from "../../context/GameContext";
import List from "../List/List";
import styles from "./ActivityTimeline.module.scss";

export default function ActivityTimeline() {
  const {
    playerActivities,
    characterActivities,
    fetchActivities,
  } = useGame();

  useEffect(() => {
    fetchActivities(); // your apiFetch wrapper
  }, [fetchActivities]);

  //   console.log("playerActivities:", playerActivities);
  //   console.log("charActivities:", characterActivities);

  const unifiedActivities = useMemo(() => {
    const player = Array.isArray(playerActivities)
      ? playerActivities.map(a => ({ ...a, source: 'player' }))
      : [];

    const character = Array.isArray(characterActivities)
      ? characterActivities.map(a => ({ ...a, source: 'character' }))
      : [];

    return [...player, ...character].sort(
      (a, b) => new Date(a.completed_at) - new Date(b.completed_at)
    );
  }, [playerActivities, characterActivities]);

  const hasAny = unifiedActivities.length > 0;

  return (
    <div className={styles.container}>
      {!hasAny && (
        <p>No activities found for this period.</p>
      )}

      {hasAny && (

        <List
          items={unifiedActivities}
          renderItem={(act) => (
            <>
            [{act.source}] {act.name || act.kind || act.description || "Untitled"} —{" "}
              {act.completed_at
                ? new Date(act.completed_at).toLocaleTimeString()
                : "No start time"}
            </>
          )}
        />
      )}
    </div>
  );
}
