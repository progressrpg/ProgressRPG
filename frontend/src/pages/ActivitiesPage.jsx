// src/pages/ActivitiesPage.jsx
import { useState, useMemo } from "react";
import { useActivities } from "../hooks/useActivities";
import { useDeleteActivity, useUpdateActivity } from "../hooks/useActivities";
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
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState("");

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

  if (isLoading) return <p>Loading activities…</p>;

  const hasActivities = activities && activities.length > 0;
  const currentTabActivities = groupedActivities[activeTab];
  const hasTabActivities = currentTabActivities && currentTabActivities.length > 0;

  const handleEditStart = (activity) => {
    setEditingId(activity.id);
    setEditingName(activity.name);
  };

  const handleEditSave = (activityId) => {
    if (editingName.trim()) {
      updateActivity.mutate({
        activityId,
        data: { name: editingName }
      });
      setEditingId(null);
      setEditingName("");
    }
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditingName("");
  };

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
              <button
                key={key}
                className={`${styles.dateButton} ${activeTab === key ? styles.active : ""}`}
                onClick={() => setActiveTab(key)}
              >
                {label}
              </button>
            ))}
          </div>

          {hasTabActivities ? (
            <div className={styles.activitiesList}>
              {Object.entries(activitiesByTab).map(([dateKey, dayActivities]) => (
                <div key={dateKey}>
                  <h3 style={{ margin: "1em 0 0.5em", fontSize: "0.95em", opacity: 0.7 }}>
                    {formatDate(new Date(dateKey))}
                  </h3>
                  {dayActivities.map((activity) => (
                    <div key={activity.id} className={styles.activityItem}>
                      <div className={styles.activityDetails}>
                        {editingId === activity.id ? (
                          <input
                            type="text"
                            className={styles.editInput}
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            autoFocus
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleEditSave(activity.id);
                              if (e.key === "Escape") handleEditCancel();
                            }}
                          />
                        ) : (
                          <div className={styles.name}>{activity.name}</div>
                        )}
                        <div className={styles.meta}>
                          Duration: {formatDuration(activity.duration)} •{" "}
                          {new Date(activity.completed_at).toLocaleTimeString("en-US", {
                            hour: "2-digit",
                            minute: "2-digit"
                          })}
                        </div>
                      </div>
                      <div className={styles.actions}>
                        {editingId === activity.id ? (
                          <>
                            <button
                              className={styles.saveButton}
                              onClick={() => handleEditSave(activity.id)}
                            >
                              Save
                            </button>
                            <button
                              className={styles.cancelButton}
                              onClick={handleEditCancel}
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              className={styles.editButton}
                              onClick={() => handleEditStart(activity)}
                            >
                              Edit
                            </button>
                            <button
                              className={styles.deleteButton}
                              onClick={() => {
                                if (confirm("Delete this activity?")) {
                                  deleteActivity.mutate(activity.id);
                                }
                              }}
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
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
