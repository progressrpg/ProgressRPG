import React, { useEffect, useRef, useState } from "react";
import classNames from "classnames";
import { AnimatePresence, motion } from "framer-motion";
import { formatDuration } from "../../utils/formatUtils";

import Button from "../Button/Button";
import AlertDialog from "../AlertDialog/AlertDialog";
import EntitySearchInput from "../EntitySearchInput/EntitySearchInput";
import SupportFlowModal from "../SupportFlow/SupportFlowModal";
import TimerResultsPanel from "./TimerResultsPanel";
import ModeSwitcher from "../ModeSwitcher/ModeSwitcher";
import TasksPanel from "../TasksPanel/TasksPanel";
import TimerNoteField from "./TimerNoteField";
import { useActivityInput } from "../ActivityInput/useActivityInput";
import { useDefaultActivityEntries } from "../../hooks/useDefaultActivityEntries";
import { useFeatureFlag } from "../../hooks/useFeatureFlag";
import styles from "./UnifiedTimerHome.module.scss";

type TimerMode = "doing" | "planning";

const TIMER_MODES = [
  { key: "doing", label: "Doing" },
  { key: "planning", label: "Planning" },
];

const fadeTransition = { duration: 0.18 };
const fadeProps = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: fadeTransition,
};

export default function UnifiedTimerHome() {
  const {
    name,
    setName,
    isActive,
    isUnlabelled,
    isEditingLabel,
    inputValue,
    taskId,
    activityCatalogId,
    elapsed,
    formattedLimit,
    showAutoStopWarning,
    flowState,
    flowDispatch,
    handleConfirmActivity,
    handleToggle,
    handleCreateActivity,
    handleUnifiedSelect,
    handleUnifiedSubmit,
    startEditingLabel,
    handleLabelBlur,
    handleLabelCancel,
    consumeJustCancelledLabelEdit,
    submitAndOpenSupport,
    openSupportMode,
    resultsData,
    exitResults,
  } = useActivityInput();

  const defaultResults = useDefaultActivityEntries();
  const notesFeatureEnabled = useFeatureFlag("notesFeature");
  const [submitConfirmOpen, setSubmitConfirmOpen] = useState(false);
  const [mode, setMode] = useState<TimerMode>("doing");
  const containerRef = useRef<HTMLDivElement>(null);

  // Label display (clickable name) only shows for a labelled, non-editing
  // running timer; every other case shows the list/input (no timer running,
  // an unlabelled running timer, or an in-progress click-to-edit).
  const showLabelDisplay = isActive && !isUnlabelled && !isEditingLabel;

  const statusMessage = showLabelDisplay
    ? `Timer running: ${inputValue || "Untitled activity"}`
    : isActive
      ? "Timer running, unlabelled"
      : "Timer stopped";

  // Click-to-edit needs the input focused immediately so the pre-filled
  // name is ready to be replaced/confirmed without an extra click.
  useEffect(() => {
    if (!isEditingLabel) return;
    containerRef.current?.querySelector("input")?.focus();
  }, [isEditingLabel]);

  // Naming an activity around planning ("plan my week", "Planning session")
  // is a strong-enough signal to drop the user straight into Planning mode
  // without an extra click. One-directional: removing "plan" later doesn't
  // switch back to Doing, since the user may have since interacted with the
  // tasks panel and an automatic yank back out would be more surprising than
  // helpful. Adjusted during render (not an effect) per React's "adjusting
  // state when a prop changes" pattern — state, not a ref, tracks the last
  // seen value so this only fires once per actual inputValue change.
  const [lastCheckedInputValue, setLastCheckedInputValue] = useState<string | null>(null);
  if (lastCheckedInputValue !== inputValue) {
    setLastCheckedInputValue(inputValue);
    if (mode !== "planning" && inputValue.toLowerCase().includes("plan")) {
      setMode("planning");
    }
  }

  // Single Start button: starting with a typed name labels the timer with
  // it. Starting with nothing typed reads as "I don't have a specific
  // activity yet" — rather than leaving the timer unlabelled, it's labelled
  // "Planning" and Planning mode opens immediately so the task list is right
  // there instead of an empty search box.
  const handleStartClick = async () => {
    if (name.trim()) {
      await handleToggle();
      return;
    }

    await handleCreateActivity("Planning");
    setMode("planning");
  };

  const handleWrapperKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape" && isEditingLabel) {
      handleLabelCancel();
      (event.target as HTMLElement).blur();
    }
  };

  const handleWrapperBlur = (event: React.FocusEvent<HTMLDivElement>) => {
    if (consumeJustCancelledLabelEdit()) return;
    if (!isEditingLabel) return;
    if (containerRef.current?.contains(event.relatedTarget as Node)) return;
    handleLabelBlur();
  };

  if (resultsData) {
    return (
      <>
        <section className={styles.wrapper}>
          <h2 className="sr-only">Activity results</h2>
          <TimerResultsPanel
            key={resultsData.activityId ?? `${resultsData.activityName ?? ""}-${resultsData.elapsedSeconds ?? 0}`}
            results={resultsData}
            onExit={exitResults}
          />
        </section>

        <SupportFlowModal
          state={flowState}
          dispatch={flowDispatch}
          onConfirmActivity={handleConfirmActivity}
        />
      </>
    );
  }

  return (
    <>
      <section className={classNames(styles.wrapper, { [styles.isActive]: isActive })}>
        <h2 className="sr-only">Activity timer</h2>
        <p className="sr-only" aria-live="polite">
          {statusMessage}
        </p>

        <motion.div
          className={styles.container}
          ref={containerRef}
          onKeyDown={handleWrapperKeyDown}
          onBlur={handleWrapperBlur}
        >
          {/* Row 1, fixed at the top regardless of state: the toggle button
              is a single persistent element (same key, never unmounted) so
              Start -> Stop is purely a label change the user perceives as
              "the same button", not a swap. Centered while idle (alone);
              once the timer fades in, the pair sits together at the right
              — `layout` on the row and on the button's wrapper animates
              that shift smoothly instead of jumping. Row 2 below is
              unaffected either way. */}
          <motion.div
            layout
            className={styles.controlsRow}
            style={{ justifyContent: isActive ? "flex-end" : "center" }}
          >
            <motion.div layout>
              <Button
                onClick={isActive ? handleToggle : handleStartClick}
                variant="primary"
                className={styles.ctaButton}
              >
                {isActive ? "Stop" : "Start"}
              </Button>
            </motion.div>

            <AnimatePresence mode="popLayout" initial={false}>
              {isActive && (
                <motion.div key="timer" layout {...fadeProps} className={styles.timerPill}>
                  {formatDuration(elapsed)}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Row 2: the activity's identity — either its label (clickable to
              edit) or the search input used to pick/type one. These are
              mutually exclusive, genuinely different elements, so they
              cross-fade; row 1 above is entirely unaffected by this swap. */}
          <motion.div className={styles.entityRow}>
            <AnimatePresence mode="popLayout" initial={false}>
              {showLabelDisplay ? (
                <motion.button
                  key="label"
                  {...fadeProps}
                  type="button"
                  className={styles.activityLabel}
                  onClick={startEditingLabel}
                  aria-label={`Editing label: ${inputValue || "Untitled activity"}. Click to change.`}
                >
                  {inputValue || "Untitled activity"}
                </motion.button>
              ) : (
                <motion.div key="search" {...fadeProps} className={styles.searchControl}>
                  <EntitySearchInput
                    type="activity"
                    value={inputValue}
                    onChange={setName}
                    onSelect={handleUnifiedSelect}
                    onCreate={handleUnifiedSubmit}
                    placeholder="What are you working on? e.g. washing dishes"
                    ariaLabel="Activity name"
                    // Always persistent/in-flow (not a floating overlay): a
                    // floating dropdown here bled outside the wrapper card
                    // and overlapped the support button below it. Reserving
                    // its space in-flow lets the card grow to actually
                    // contain the list instead.
                    alwaysOpen
                    defaultResults={defaultResults}
                    maxVisibleRows={4}
                    emptyMessage="Looking for a match..."
                    className={styles.entitySearch}
                    inputClassName={styles.inputText}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>

        {isActive && (
          <>
            {notesFeatureEnabled && mode === "doing" && (taskId !== null || activityCatalogId !== null) && (
              <TimerNoteField taskId={taskId} activityId={activityCatalogId} />
            )}

            <ModeSwitcher
              modes={TIMER_MODES}
              activeKey={mode}
              onSelect={(key) => setMode(key as TimerMode)}
              ariaLabel="Timer view"
              className={styles.modeSwitcher}
            />

            {mode === "planning" && (
              <div className={styles.planningPanel}>
                <TasksPanel />
              </div>
            )}
          </>
        )}

        {showAutoStopWarning && (
          <p className={styles.limitWarning}>
            This timer will stop automatically when it reaches {formattedLimit}.
          </p>
        )}

        <div className={styles.supportButtonRow}>
          <Button
            onClick={() => {
              if (isActive) {
                setSubmitConfirmOpen(true);
              } else {
                openSupportMode();
              }
            }}
            variant="secondary"
            className={styles.supportModeButton}
            ariaLabel="Open support mode"
          >
            Need support?
          </Button>
        </div>
      </section>

      <AlertDialog
        open={submitConfirmOpen}
        title="Submit active timer?"
        description="You already have a timer running. Submit it before opening Task Support?"
        confirmLabel="Submit & continue"
        cancelLabel="Cancel"
        onCancel={() => setSubmitConfirmOpen(false)}
        onConfirm={() => {
          setSubmitConfirmOpen(false);
          submitAndOpenSupport();
        }}
      />

      <SupportFlowModal
        state={flowState}
        dispatch={flowDispatch}
        onConfirmActivity={handleConfirmActivity}
      />
    </>
  );
}
