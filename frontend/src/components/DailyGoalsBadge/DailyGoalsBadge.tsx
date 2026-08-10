import React from "react";
import { useDailyGoals } from "../../hooks/usePlayer";
import styles from "./DailyGoalsBadge.module.scss";

interface GoalItem {
  key: string;
  label: string;
  met: boolean;
}

// Personal "daily goals" badge for the map view (issue #751, replacing the
// old single-number "today" points badge from issue #673) - deliberately
// not attached to any village marker, and deliberately silent about the
// player/character link: framed as the player's own goals rather than
// naming a character, since players don't yet know about the link.
// Renders nothing (not an empty/all-unmet state) when the player has no
// active PlayerCharacterLink - see MeViewSet.daily_goals in api/views.py.
export default function DailyGoalsBadge(): React.ReactElement | null {
  const { data } = useDailyGoals();
  const goals = data?.goals;

  if (goals == null) {
    return null;
  }

  const items: GoalItem[] = [
    { key: "login", label: "Logged in today", met: goals.logged_in_today },
    {
      key: "activity",
      label: "Completed an activity",
      met: goals.completed_activity_today,
    },
    {
      key: "minutes",
      label: `${goals.minutes_goal_threshold}+ minutes recorded`,
      met: goals.minutes_goal_met,
    },
  ];

  return (
    <div className={styles.badge} aria-live="polite" role="status">
      <p className={styles.title}>Today&apos;s goals</p>
      <ul className={styles.goalList}>
        {items.map((item) => (
          <li
            key={item.key}
            className={item.met ? styles.goalMet : styles.goal}
          >
            <span className={styles.goalMark} aria-hidden="true">
              {item.met ? "✓" : "○"}
            </span>
            {item.label}
          </li>
        ))}
      </ul>
      {goals.all_goals_met && (
        <p className={styles.bonus}>
          {goals.bonus_awarded_today
            ? `+${goals.bonus_ap} AP bonus earned!`
            : "All goals cleared!"}
        </p>
      )}
    </div>
  );
}
