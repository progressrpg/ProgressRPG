// SupportFlow/screens/ActivityInputScreen.tsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import * as Tabs from "../../Tabs/Tabs";
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { ACTIVITY_PRESETS } from "../supportFlowReducer";
import { useFeatureFlag } from "../../../hooks/useFeatureFlag";
import { useTasks } from "../../../hooks/useTasks";
import styles from "../SupportFlowModal.module.scss";
import type { Task } from "../../../types/domain";

interface ActivityInputScreenProps {
  activityPresetId?: string | null;
  activityText?: string;
  onChangeText?: (text: string) => void;
  onConfirm?: () => void | Promise<void>;
  onConfirmWithText?: (text: string, taskId?: number | null) => void | Promise<void>;
}

export default function ActivityInputScreen({
  activityPresetId,
  activityText = "",
  onChangeText,
  onConfirm,
  onConfirmWithText,
}: ActivityInputScreenProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const preset = activityPresetId ? ACTIVITY_PRESETS[activityPresetId as keyof typeof ACTIVITY_PRESETS] : undefined;
  const isExamplesOnlyPreset = activityPresetId === "tiniest_step";
  const isPriorityThreePreset = activityPresetId === "priority_three";
  const [candidateTasks, setCandidateTasks] = useState<string[]>(["", "", ""]);
  const [activeTab, setActiveTab] = useState<"memory" | "tasks">("memory");

  const tasksFeatureEnabled = useFeatureFlag("tasksFeature");
  const showTabs = isPriorityThreePreset && tasksFeatureEnabled;

  const { data: allTasks } = useTasks({ enabled: showTabs });
  const incompleteTasks: Task[] = useMemo(
    () => (allTasks ?? []).filter((t) => !t.is_complete && !t.completed_at),
    [allTasks]
  );

  useEffect(() => {
    if (!isExamplesOnlyPreset && !isPriorityThreePreset) {
      inputRef.current?.focus();
    }
  }, [isExamplesOnlyPreset, isPriorityThreePreset]);

  const placeholder = preset?.placeholder ?? "What are you going to do?";
  const hint = preset?.hint ?? null;

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && activityText.trim()) {
      e.preventDefault();
      onConfirm?.();
    }
  }

  function handleCandidateChange(index: number, value: string) {
    setCandidateTasks((previous) => {
      const next = [...previous];
      next[index] = value;
      return next;
    });
  }

  function handleStartCandidate(index: number) {
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

  function handleStartTask(task: Task) {
    onConfirmWithText?.(task.name, task.id);
  }

  function handleRandomiseFromTasks() {
    if (!incompleteTasks.length) return;
    const task = incompleteTasks[Math.floor(Math.random() * incompleteTasks.length)];
    onConfirmWithText?.(task.name, task.id);
  }

  return (
    <div className={styles.activityInputScreen}>
      {!isPriorityThreePreset && (
        <p className={styles.readableText}>
          {isExamplesOnlyPreset
            ? "Write down your next tiny action on paper or your phone."
            : "Describe what you'll do:"}
        </p>
      )}

      {isExamplesOnlyPreset && (
        <p className={`${styles.hint} ${styles.readableText}`}>
          Example: if your task is washing dishes, your first step can be "stand up and walk to the kitchen". After you write something down, you have permission to just breathe for the rest of the timer.
        </p>
      )}

      {hint && !isExamplesOnlyPreset && !isPriorityThreePreset && (
        <p className={`${styles.hint} ${styles.readableText}`}>{hint}</p>
      )}

      {!isExamplesOnlyPreset && !isPriorityThreePreset && (
        <textarea
          ref={inputRef}
          className={styles.activityTextArea}
          value={activityText}
          onChange={(e) => onChangeText?.(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={3}
          aria-label="Activity description"
        />
      )}

      {isPriorityThreePreset && (
        <Tabs.Root
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as "memory" | "tasks")}
        >
          {showTabs && (
            <Tabs.List className={styles.tabBar}>
              <Tabs.Trigger
                value="memory"
                className={`${styles.tab} ${activeTab === "memory" ? styles.tabActive : ""}`}
              >
                From memory
              </Tabs.Trigger>
              <Tabs.Trigger
                value="tasks"
                className={`${styles.tab} ${activeTab === "tasks" ? styles.tabActive : ""}`}
              >
                My tasks
              </Tabs.Trigger>
            </Tabs.List>
          )}

          <Tabs.Content value="memory">
            <div className={styles.priorityThreeContainer}>
              <p className={styles.readableText}>Write down the first three things that come into your head.</p>
              {hint && <p className={`${styles.hint} ${styles.readableText}`}>{hint}</p>}
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
          </Tabs.Content>

          <Tabs.Content value="tasks">
            <div className={styles.priorityThreeContainer}>
              {incompleteTasks.length === 0 ? (
                <p className={styles.taskPickEmpty}>
                  {allTasks === undefined ? "Loading tasks…" : "No incomplete tasks yet. Add some on the Tasks page."}
                </p>
              ) : (
                <>
                  <div className={styles.taskPickList}>
                    {incompleteTasks.map((task) => (
                      <div key={task.id} className={styles.taskPickRow}>
                        <span className={styles.taskPickName}>{task.name}</span>
                        <Button onClick={() => handleStartTask(task)}>Start this</Button>
                      </div>
                    ))}
                  </div>
                  <Button onClick={handleRandomiseFromTasks}>
                    Randomise and start
                  </Button>
                </>
              )}
            </div>
          </Tabs.Content>
        </Tabs.Root>
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
