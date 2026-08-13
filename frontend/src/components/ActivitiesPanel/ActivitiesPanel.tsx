import { useDeleteActivity, useUpdateActivity } from "../../hooks/useActivities";
import { useActivities } from "../../hooks/useActivities";
import { useMemo, useCallback, useState } from "react";
import type { PlayerActivity } from "../../types";
import { formatDurationShort, pluralize } from "../../utils/formatUtils";

import Button from "../Button/Button";
import PlayerItemList from "../PlayerItemList/PlayerItemList";
import Tooltip from "../Tooltip/Tooltip";
import LogOfflineActivityModal from "../LogOfflineActivityModal/LogOfflineActivityModal";
import styles from "./ActivitiesPanel.module.scss";

type DateCategory = "today" | "yesterday" | "older";

// Helper to format date for display
const formatDate = (date: Date): string => {
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

interface BucketedActivity {
  activity: PlayerActivity;
  category: DateCategory;
  dateKey: string;
  timestamp: number;
}

// Bucket every activity by date category (today/yesterday/older) and day key in a single pass,
// parsing each activity's completed_at exactly once.
const bucketActivities = (activities: PlayerActivity[]): BucketedActivity[] => {
  const today = new Date().toDateString();
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayString = yesterday.toDateString();

  return activities.map((activity) => {
    const date = new Date(activity.completed_at ?? "");
    const valid = !isNaN(date.getTime());
    const dateOnly = valid ? date.toDateString() : "";

    const category: DateCategory = !valid
      ? "older"
      : dateOnly === today
        ? "today"
        : dateOnly === yesterdayString
          ? "yesterday"
          : "older";

    return {
      activity,
      category,
      dateKey: valid ? date.toISOString().split("T")[0] : "invalid",
      timestamp: valid ? date.getTime() : 0,
    };
  });
};

export default function ActivitiesPanel(): React.ReactElement | null {
  const { data: activities, isLoading } = useActivities();
  const deleteActivity = useDeleteActivity();
  const updateActivity = useUpdateActivity();
  const [activeTab, setActiveTab] = useState<DateCategory>("today");
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);

  const bucketed = useMemo(() => bucketActivities(activities ?? []), [activities]);

  const groupedByCategory = useMemo(() => {
    const grouped: Record<DateCategory, BucketedActivity[]> = { today: [], yesterday: [], older: [] };
    bucketed.forEach((entry) => grouped[entry.category].push(entry));
    (Object.keys(grouped) as DateCategory[]).forEach((key) => {
      grouped[key].sort((a, b) => b.timestamp - a.timestamp);
    });
    return grouped;
  }, [bucketed]);

  // Group the active tab's activities by day key, reusing the category/date-key computed above.
  const activitiesByDay = useMemo(() => {
    const byDate: Record<string, PlayerActivity[]> = {};
    groupedByCategory[activeTab].forEach(({ activity, dateKey }) => {
      if (!byDate[dateKey]) byDate[dateKey] = [];
      byDate[dateKey].push(activity);
    });
    return byDate;
  }, [groupedByCategory, activeTab]);

  const dateTabs = useMemo(
    () => [
      { key: "older" as const, label: `Older (${groupedByCategory.older.length})` },
      { key: "yesterday" as const, label: `Yesterday (${groupedByCategory.yesterday.length})` },
      { key: "today" as const, label: `Today (${groupedByCategory.today.length})` },
    ],
    [groupedByCategory],
  );

  const hasActivities = bucketed.length > 0;
  const hasTabActivities = groupedByCategory[activeTab].length > 0;

  const handleEdit = useCallback(
    (activity: PlayerActivity, name: string, callbacks?: { onSuccess?: () => void; onError?: () => void }) => {
      updateActivity.mutate(
        {
          activityId: activity.id,
          data: { name },
        },
        callbacks,
      );
    },
    [updateActivity],
  );

  const handleDelete = useCallback(
    (activity: PlayerActivity) => {
      deleteActivity.mutate(activity.id);
    },
    [deleteActivity],
  );

  if (isLoading) return <p>Loading activities…</p>;

  return (
    <div className={styles.page}>
      <div className={styles.content}>
      <div className={styles.toolbar}>
        {hasActivities && (
          <div className={styles.dateTabs}>
            {dateTabs.map(({ key, label }) => (
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
        )}
        <Tooltip content="Add offline activity">
          <button
            type="button"
            className={styles.addOfflineButton}
            aria-label="Add offline activity"
            onClick={() => setIsLogModalOpen(true)}
          >
            +
          </button>
        </Tooltip>
      </div>

      {isLogModalOpen && (
        <LogOfflineActivityModal onClose={() => setIsLogModalOpen(false)} />
      )}

      {hasActivities && (
        <>
          {hasTabActivities ? (
            <div className={styles.activitiesList}>
              {Object.entries(activitiesByDay).map(([dateKey, dayActivities]) => {
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
                    <h2 className={styles.dayHeading}>
                      {headingLabel} ({dayActivities.length} {pluralize(dayActivities.length, "activity", "activities")}, {formatDurationShort(dayDurationTotalSeconds)}, {dayXpTotal} XP)
                    </h2>
                    <PlayerItemList<PlayerActivity>
                      items={dayActivities}
                      itemLabel="activity"
                      ariaLabel={`Activities for ${headingLabel}`}
                      renderItemMeta={(activity) => (
                        <>
                          Duration: {formatDurationShort(Number(activity.duration) || 0)} •{" "}
                          {Number(activity.xp_gained) || 0} XP gained •{" "}
                          {new Date(activity.completed_at ?? 0).toLocaleTimeString("en-US", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </>
                      )}
                      renderEditSummary={(activity) => (
                        <>
                          Duration: {formatDurationShort(Number(activity.duration) || 0)} • Completed:{" "}
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
    </div>
  );
}
