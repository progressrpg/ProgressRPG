// SupportFlow/screens/ActivityInputScreen.jsx
import { useEffect, useRef } from "react";
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { ACTIVITY_PRESETS } from "../supportFlowReducer";
import styles from "../SupportFlowModal.module.scss";

export default function ActivityInputScreen({
  activityPresetId,
  activityText,
  onChangeText,
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
  const hint = preset?.hint ?? null;

  function handleKeyDown(e) {
    // Enter (without Shift) submits, same as clicking "Start activity"
    if (e.key === "Enter" && !e.shiftKey && activityText.trim()) {
      e.preventDefault();
      onConfirm();
    }
  }

  return (
    <div className={styles.activityInputScreen}>
      <p>Describe what you&apos;ll do:</p>

      {hint && <p className={styles.hint}>{hint}</p>}

      <textarea
        ref={inputRef}
        className={styles.activityTextArea}
        value={activityText}
        onChange={(e) => onChangeText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={3}
        aria-label="Activity description"
      />

      <ButtonFrame>
        <Button onClick={onConfirm} disabled={!activityText.trim()}>
          Start activity
        </Button>
        <Button onClick={onBack}>
          Back
        </Button>
      </ButtonFrame>
    </div>
  );
}
