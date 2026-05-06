// src/pages/ActivitiesPage.jsx
import { useDeleteActivity, useUpdateActivity } from "../hooks/useActivities";
import { useActivities } from "../hooks/useActivities";
import { useMemo, useCallback, useState } from "react";

import Button from "../components/Button/Button";
import PlayerItemList from "../components/PlayerItemList/PlayerItemList";
import styles from "./ActivitiesPage.module.scss";

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

// Helper to format date for display
const formatDate = (date) => {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";

  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric"
  });
};

// Helper to get date key for grouping
const getDateKey = (dateString) => {
  const date = new Date(dateString);
  if (isNaN(date.getTime())) {
    // Return a fallback key for invalid dates
    return "invalid";
  }
  return date.toISOString().split('T')[0];
};

// Helper to check if activity is from today, yesterday, or older
const getActivityDateCategory = (dateString) => {
  const activityDate = new Date(dateString);

  // Handle invalid dates
  if (isNaN(activityDate.getTime())) {
    return "older";
  }

  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const activityDateOnly = activityDate.toDateString();

  if (activityDateOnly === today.toDateString()) return "today";
  if (activityDateOnly === yesterday.toDateString()) return "yesterday";
  return "older";
};

export default function ActivitiesPage() {
  const { data: activities, isLoading } = useActivities();
  const deleteActivity = useDeleteActivity();
  const updateActivity = useUpdateActivity();
  const [activeTab, setActiveTab] = useState("today");

  // Group activities by date
  const groupedActivities = useMemo(() => {
    if (!activities) return { today: [], yesterday: [], older: [] };

    const grouped = { today: [], yesterday: [], older: [] };

    activities.forEach((activity) => {
      const category = getActivityDateCategory(activity.completed_at);
      grouped[category].push(activity);
    });

    // Sort each group by date (newest first)
    Object.keys(grouped).forEach((key) => {
      grouped[key].sort((a, b) => {
        const dateA = new Date(a.completed_at);
        const dateB = new Date(b.completed_at);
        return dateB - dateA;
      });
    });

    return grouped;
  }, [activities]);

  // Get activities for active tab, grouped by date
  const activitiesByTab = useMemo(() => {
    const tabActivities = groupedActivities[activeTab];
    const byDate = {};

    tabActivities.forEach((activity) => {
      const dateKey = getDateKey(activity.completed_at);
      if (!byDate[dateKey]) {
        byDate[dateKey] = [];
      }
      byDate[dateKey].push(activity);
    });

    return byDate;
  }, [groupedActivities, activeTab]);

  const hasActivities = activities && activities.length > 0;
  const currentTabActivities = groupedActivities[activeTab];
  const hasTabActivities = currentTabActivities && currentTabActivities.length > 0;

  const handleEdit = useCallback(
    (activity, name) => {
      updateActivity.mutate({
        activityId: activity.id,
        data: { name },
      });
    },
    [updateActivity],
  );

  const handleDelete = useCallback(
    (activity) => {
      deleteActivity.mutate(activity.id);
    },
    [deleteActivity],
  );

  if (isLoading) return <p>Loading activities…</p>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Activities</h1>
      </div>

      {hasActivities && (
        <>
          <div className={styles.dateTabs}>
            {[
              { key: "older", label: `Older (${groupedActivities.older.length})` },
              { key: "yesterday", label: `Yesterday (${groupedActivities.yesterday.length})` },
              { key: "today", label: `Today (${groupedActivities.today.length})` },
            ].map(({ key, label }) => (
              <Button
                key={key}
                variant={activeTab === key ? "primary" : "secondary"}
                className={`${styles.dateButton} ${activeTab === key ? styles.active : ""}`}
                onClick={() => setActiveTab(key)}
              >
                {label}
              </Button>
            ))}
          </div>

          {hasTabActivities ? (
            <div className={styles.activitiesList}>
              {Object.entries(activitiesByTab).map(([dateKey, dayActivities]) => {
                const dayDurationTotalSeconds = dayActivities.reduce(
                  (sum, activity) => sum + (Number(activity.duration) || 0),
                  0,
                );
                const dayXpTotal = dayActivities.reduce(
                  (sum, activity) => sum + (Number(activity.xp_gained) || 0),
                  0,
                );
                const headingLabel = formatDate(new Date(dateKey));

                return (
                  <div key={dateKey}>
                    <h3 style={{ margin: "1em 0 0.5em", fontSize: "0.95em", opacity: 0.7 }}>
                      {headingLabel} ({dayActivities.length} {dayActivities.length === 1 ? 'activity' : 'activities'}, {formatDuration(dayDurationTotalSeconds)}, {dayXpTotal} XP)
                    </h3>
                    <PlayerItemList
                      items={dayActivities}
                      itemLabel="activity"
                      ariaLabel={`Activities for ${headingLabel}`}
                      renderItemMeta={(activity) => (
                        <>
                          Duration: {formatDuration(Number(activity.duration) || 0)} •{" "}
                          {Number(activity.xp_gained) || 0} XP gained •{" "}
                          {new Date(activity.completed_at).toLocaleTimeString("en-US", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </>
                      )}
                      renderEditSummary={(activity) => (
                        <>
                          Duration: {formatDuration(Number(activity.duration) || 0)} • Completed:{" "}
                          {activity?.completed_at
                            ? new Date(activity.completed_at).toLocaleTimeString("en-US", {
                                hour: "2-digit",
                                minute: "2-digit",
                              })
                            : "-"}{" "}
                          • {Number(activity.xp_gained) || 0} XP gained
                        </>
                      )}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                    />
                  </div>
                );
              })}
            </div>
          ) : (
            <div className={styles.emptyState}>
              <p>No activities for this period.</p>
            </div>
          )}
        </>
      )}

      {!hasActivities && (
        <div className={styles.emptyState}>
          <p>No activities recorded yet.</p>
        </div>
      )}
    </div>
  );
}
