// src/pages/ActivitiesPage.jsx
import { useState, useMemo, useCallback } from "react";
import { useActivities } from "../hooks/useActivities";
import { useDeleteActivity, useUpdateActivity } from "../hooks/useActivities";
import Button from "../components/Button/Button";
import Modal from "../components/Modal/Modal";
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
  const [activityPendingDelete, setActivityPendingDelete] = useState(null);

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

  const handleEditStart = (activity) => {
    setEditingId(activity.id);
    setEditingName(activity.name);
  };

  const handleEditSave = () => {
    if (!editingId) return;
    if (editingName.trim()) {
      updateActivity.mutate({
        activityId: editingId,
        data: { name: editingName }
      });
      setEditingId(null);
      setEditingName("");
    }
  };

  const handleEditCancel = useCallback(() => {
    setEditingId(null);
    setEditingName("");
  }, []);

  const handleDeleteRequest = (activity) => {
    setActivityPendingDelete(activity);
  };

  const handleDeleteCancel = useCallback(() => {
    setActivityPendingDelete(null);
  }, []);

  const handleDeleteConfirm = () => {
    if (!activityPendingDelete?.id) return;
    deleteActivity.mutate(activityPendingDelete.id);
    setActivityPendingDelete(null);
  };

  const editingActivity = activities?.find((activity) => activity.id === editingId) || null;
  const editingActivityDurationLabel = editingActivity
    ? formatDuration(Number(editingActivity.duration) || 0)
    : "-";
  const editingActivityCompletedTimeLabel = editingActivity?.completed_at
    ? new Date(editingActivity.completed_at).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "-";
  const editingActivityXpLabel = editingActivity
    ? Number(editingActivity.xp_gained) || 0
    : 0;

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
              {Object.entries(activitiesByTab).map(([dateKey, dayActivities]) => (
                <div key={dateKey}>
                  {(() => {
                    const dayDurationTotalSeconds = dayActivities.reduce(
                      (sum, activity) => sum + (Number(activity.duration) || 0),
                      0
                    );
                    const dayXpTotal = dayActivities.reduce(
                      (sum, activity) => sum + (Number(activity.xp_gained) || 0),
                      0
                    );
                    const headingLabel = formatDate(new Date(dateKey));

                    return (
                  <h3 style={{ margin: "1em 0 0.5em", fontSize: "0.95em", opacity: 0.7 }}>
                    {headingLabel} ({dayActivities.length} {dayActivities.length === 1 ? 'activity' : 'activities'}, {formatDuration(dayDurationTotalSeconds)}, {dayXpTotal} XP)
                  </h3>
                    );
                  })()}
                  {dayActivities.map((activity) => (
                    <div key={activity.id} className={styles.activityItem}>
                      <div className={styles.activityDetails}>
                        <div className={styles.name}>{activity.name}</div>
                        <div className={styles.meta}>
                          Duration: {formatDuration(activity.duration)} •{" "}
                          {activity.xp_gained} XP gained •{" "}
                          {new Date(activity.completed_at).toLocaleTimeString("en-US", {
                            hour: "2-digit",
                            minute: "2-digit"
                          })}
                        </div>
                      </div>
                      <div className={styles.actions}>
                        <>
                          <Button
                            variant="secondary"
                            className={styles.editButton}
                            onClick={() => handleEditStart(activity)}
                          >
                            Edit
                          </Button>
                          <Button
                            variant="secondaryDanger"
                            className={styles.deleteButton}
                            onClick={() => handleDeleteRequest(activity)}
                          >
                            Delete
                          </Button>
                        </>
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

      {activityPendingDelete && (
        <Modal
          id="delete-activity-modal"
          title="Delete activity?"
          onClose={handleDeleteCancel}
        >
          <div className={styles.deleteConfirmContent}>
            <p>
              Are you sure you want to delete
              {activityPendingDelete.name ? ` "${activityPendingDelete.name}"` : " this activity"}?
            </p>
            <div className={styles.deleteConfirmActions}>
              <Button variant="secondary" onClick={handleDeleteCancel}>
                Cancel
              </Button>
              <Button variant="danger" onClick={handleDeleteConfirm}>
                Delete
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {editingId && (
        <Modal
          id="edit-activity-modal"
          title="Edit activity"
          onClose={handleEditCancel}
        >
          <div className={styles.editConfirmContent}>
            <p className={styles.editConfirmMeta}>
              Duration: {editingActivityDurationLabel} • Completed: {editingActivityCompletedTimeLabel} • {editingActivityXpLabel} XP gained
            </p>
            <p>
              Update activity name
              {editingActivity?.name ? ` for "${editingActivity.name}"` : ""}:
            </p>
            <input
              type="text"
              className={styles.editInput}
              value={editingName}
              onChange={(e) => setEditingName(e.target.value)}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleEditSave();
                if (e.key === "Escape") handleEditCancel();
              }}
            />
            <div className={styles.editConfirmActions}>
              <Button variant="secondary" onClick={handleEditCancel}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleEditSave}>
                Save
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
