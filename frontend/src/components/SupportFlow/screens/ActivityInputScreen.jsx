// SupportFlow/screens/ActivityInputScreen.jsx
import { useEffect, useRef } from "react";
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { ACTIVITY_PRESETS } from "../supportFlowReducer";
import styles from "../SupportFlowModal.module.scss";

export default function ActivityInputScreen({
  activityPresetId,
  activityText,
  durationSeconds,
  onChangeText,
  onChangeDuration,
  onConfirm,
  onBack,
}) {
  const inputRef = useRef(null);

  // Focus the text input when the screen mounts
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const preset = ACTIVITY_PRESETS[activityPresetId];
  const placeholder = preset?.placeholder ?? "What are you going to do?";

  const durationMinutes =
    typeof durationSeconds === "number" ? Math.round(durationSeconds / 60) : "";

  function handleDurationChange(e) {
    const raw = e.target.value;
    if (raw === "") {
      onChangeDuration(null);
    } else {
      const mins = parseInt(raw, 10);
      if (!isNaN(mins) && mins > 0) {
        onChangeDuration(mins * 60);
      }
    }
  }

  return (
    <div className={styles.activityInputScreen}>
      <p>Describe what you&apos;ll do:</p>

      <textarea
        ref={inputRef}
        className={styles.activityTextArea}
        value={activityText}
        onChange={(e) => onChangeText(e.target.value)}
        placeholder={placeholder}
        rows={3}
        aria-label="Activity description"
      />

      <div className={styles.durationRow}>
        <label htmlFor="support-duration" className={styles.durationLabel}>
          Time limit (minutes, optional):
        </label>
        <input
          id="support-duration"
          className={styles.durationInput}
          type="number"
          min={1}
          value={durationMinutes}
          onChange={handleDurationChange}
          placeholder="e.g. 5"
          aria-label="Optional time limit in minutes"
        />
      </div>

      <ButtonFrame>
        <Button onClick={onConfirm} disabled={!activityText.trim()}>
          Start activity
        </Button>
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
      </ButtonFrame>
    </div>
  );
}
