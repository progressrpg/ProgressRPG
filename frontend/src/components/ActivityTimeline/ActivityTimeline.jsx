import { useMemo, useEffect } from "react";
import { Link } from "react-router-dom";
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
    fetchActivities();
  }, [fetchActivities]);

  //console.log("playerActivities:", playerActivities);
  //console.log("charActivities:", characterActivities);

  const unifiedActivities = useMemo(() => {
    const combined = [...playerActivities, ...characterActivities].sort(
      (a, b) => {
        const at = a.completed_at ? new Date(a.completed_at).getTime() : 0
        const bt = b.completed_at ? new Date(b.completed_at).getTime() : 0
        return at - bt;
      }
    );

    // Add header item at the beginning
    return [{ id: 'header', isHeader: true }, ...combined];
  }, [playerActivities, characterActivities]);

  const hasAny = unifiedActivities.length > 0;

  return (
    <div className={styles.container}>
      <Link to="/activities" className={styles.activitiesLink}>
        View past activities
      </Link>

      {!hasAny && (
        <p>No activities found for this period.</p>
      )}

      {hasAny && (

        <List
          items={unifiedActivities}
          getKey={(act) => `${act.source}-${act.id ?? i}`}
          renderItem={(act) => (
            <div className={styles.line}>
              {act.player ? 'You' : character?.first_name || 'Character' } finished <strong>{act.name.toLowerCase() || act.kind || "an activity"}</strong> —{" "}
              {act.completed_at
                ? new Date(act.completed_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })
                : "Not completed"}
            </div>
          )}
        />
      )}
    </div>
  );
}
