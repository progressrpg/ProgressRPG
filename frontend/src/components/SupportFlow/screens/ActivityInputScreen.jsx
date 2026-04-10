// SupportFlow/screens/ActivityInputScreen.jsx
import { useEffect, useMemo, useRef, useState } from "react";
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { ACTIVITY_PRESETS } from "../supportFlowReducer";
import styles from "../SupportFlowModal.module.scss";

export default function ActivityInputScreen({
  activityPresetId,
  activityText,
  onChangeText,
  onConfirm,
  onConfirmWithText,
}) {
  const inputRef = useRef(null);
  const preset = ACTIVITY_PRESETS[activityPresetId];
  const isExamplesOnlyPreset = activityPresetId === "tiniest_step";
  const isPriorityThreePreset = activityPresetId === "priority_three";
  const [candidateTasks, setCandidateTasks] = useState(["", "", ""]);

  // Focus the text input when editable input is shown
  useEffect(() => {
    if (!isExamplesOnlyPreset && !isPriorityThreePreset) {
      inputRef.current?.focus();
    }
  }, [isExamplesOnlyPreset, isPriorityThreePreset]);

  useEffect(() => {
    setCandidateTasks(["", "", ""]);
  }, [activityPresetId]);

  const placeholder = preset?.placeholder ?? "What are you going to do?";
  const hint = preset?.hint ?? null;

  function handleKeyDown(e) {
    // Enter (without Shift) submits the current activity input.
    if (e.key === "Enter" && !e.shiftKey && activityText.trim()) {
      e.preventDefault();
      onConfirm();
    }
  }

  function handleCandidateChange(index, value) {
    setCandidateTasks((previous) => {
      const next = [...previous];
      next[index] = value;
      return next;
    });
  }

  function handleStartCandidate(index) {
    const selected = candidateTasks[index]?.trim();
    if (!selected) return;
    onConfirmWithText?.(selected);
  }

  const filledCandidates = useMemo(
    () => candidateTasks.map((task) => task.trim()).filter(Boolean),
    [candidateTasks]
  );

  function handleRandomizeStart() {
    if (!filledCandidates.length) return;
    const randomIndex = Math.floor(Math.random() * filledCandidates.length);
    onConfirmWithText?.(filledCandidates[randomIndex]);
  }

  return (
    <div className={styles.activityInputScreen}>
      <p>
        {isExamplesOnlyPreset
          ? "Write down one tiny first step from these examples:"
          : isPriorityThreePreset
            ? "Write down the first three tasks that come into your head."
            : "Describe what you'll do:"}
      </p>

      {hint && <p className={styles.hint}>{hint}</p>}

      {!isExamplesOnlyPreset && !isPriorityThreePreset && (
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
      )}

      {isPriorityThreePreset && (
        <div className={styles.priorityThreeContainer}>
          {[0, 1, 2].map((index) => {
            const taskValue = candidateTasks[index];
            const taskNumber = index + 1;
            return (
              <div className={styles.priorityRow} key={`priority-task-${taskNumber}`}>
                <input
                  className={styles.priorityInput}
                  type="text"
                  value={taskValue}
                  onChange={(e) => handleCandidateChange(index, e.target.value)}
                  placeholder={`Task ${taskNumber}`}
                  aria-label={`Task option ${taskNumber}`}
                />
                <Button
                  onClick={() => handleStartCandidate(index)}
                  disabled={!taskValue.trim()}
                >
                  Start this
                </Button>
              </div>
            );
          })}
          <Button onClick={handleRandomizeStart} disabled={filledCandidates.length === 0}>
            Randomise and start
          </Button>
        </div>
      )}

      {!isPriorityThreePreset && (
        <ButtonFrame>
          <Button onClick={() => onConfirm?.()} disabled={!activityText.trim()}>
            {isExamplesOnlyPreset ? "Write it down" : "Start activity"}
          </Button>
        </ButtonFrame>
      )}
    </div>
  );
}
