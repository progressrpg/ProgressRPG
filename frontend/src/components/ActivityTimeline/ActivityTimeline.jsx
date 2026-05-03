import { useMemo, useEffect } from "react";
import { Link } from "react-router-dom";
import { useGame } from "../../context/GameContext";
import List from "../List/List";
import styles from "./ActivityTimeline.module.scss";


// Helper to format duration nicely
const formatDuration = (seconds) => {
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
};

export default function ActivityTimeline() {
  const {
    playerActivities,
    characterActivities,
    fetchActivities,
    character,
    player,
    freeTimerLimitSeconds,
    activityTimer,
    loading,
  } = useGame();

  const isPremium = Boolean(player?.is_premium);

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
      <h3 className={styles.heading}>
        Recent activities
      </h3>

      {!hasAny && (
        <p>No activities found for this period.</p>
      )}

      {hasAny && (

        <List
          items={unifiedActivities}
          getKey={(act, i) => `${act.player ? 'player' : 'character'}-${act.id ?? i}`}
          getItemClassName={() => styles.activityLineItem}
          renderItem={(act) => (
            <div className={styles.line}>
              <span className={styles.lineText}>
                {act.player ? 'You' : character?.first_name || 'Character' } finished <strong>{act.name?.toLowerCase() || act.kind || "an activity"}</strong> —{" "}
                {formatDuration(act.duration)}
              </span>
              <button
                type="button"
                className={styles.playButton}
                onClick={async (event) => {
                  event.currentTarget.blur();

                  const activityText = (act.name || act.kind || "").trim();
                  if (!activityText) return;
                  if (activityTimer?.status === "active") return;

                  await activityTimer?.startActivity({
                    text: activityText,
                    limitSeconds: isPremium ? null : freeTimerLimitSeconds,
                  });
                }}
                aria-label={`Restart ${act.name || act.kind || "activity"}`}
                title="Do this activity again"
              >
                ▷
              </button>
              {/* {act.completed_at
                ? new Date(act.completed_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })
                : "Not completed"} */}
            </div>
          )}
        />
      )}
    </div>
  );
}
