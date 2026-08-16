import React from "react";

import { useTimerNote } from "../../hooks/useTimerNote";
import styles from "./UnifiedTimerHome.module.scss";

interface TimerNoteFieldProps {
  taskId: number | null;
  activityId: number | null;
}

/**
 * Freeform note for whatever's being timed, shown under the label row while
 * a timer is actively running. Saves on blur (same trigger as the running
 * timer's own label) rather than on every keystroke.
 */
export default function TimerNoteField({ taskId, activityId }: TimerNoteFieldProps) {
  const { value, setValue, save, enabled } = useTimerNote({ taskId, activityId });

  if (!enabled) return null;

  return (
    <textarea
      className={styles.noteField}
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={save}
      placeholder="Jot a note about this..."
      aria-label="Note for what you're timing"
      rows={2}
    />
  );
}
