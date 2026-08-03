import React from "react";
import { useTodayPoints } from "../../hooks/usePlayer";
import styles from "./TodayPointsBadge.module.scss";

// Personal "points earned today" badge for the map view (issue #673) -
// deliberately not attached to any village marker, and deliberately silent
// about the player/character link: framed as "you contributed today" rather
// than naming a character, since players don't yet know about the link.
// Renders nothing (not a zero) when the player has no active
// PlayerCharacterLink - see MeViewSet.today_points in api/views.py.
export default function TodayPointsBadge(): React.ReactElement | null {
  const { data } = useTodayPoints();

  if (data?.points_today == null) {
    return null;
  }

  return (
    <div className={styles.badge} aria-live="polite" role="status">
      You contributed {data.points_today} today
    </div>
  );
}
