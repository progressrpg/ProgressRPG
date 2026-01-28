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
    character,
    loading,
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
        return bt - at;
      }
    );
    return combined;
  }, [playerActivities, characterActivities]);


  const hasAny = unifiedActivities.length > 0;

  if (loading) {
    return (
      <div className={styles.infoBar} role="status" aria-live="polite" aria-busy="true">
        <span className="sr-only">Loading data...</span>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* <Link to="/activities" className={styles.activitiesLink}>
        View past activities
      </Link> */}
      <h3>
        Recent activities
      </h3>

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
