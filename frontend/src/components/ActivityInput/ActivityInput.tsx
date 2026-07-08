import React, { useState } from "react";
import classNames from "classnames";

import Button from "../Button/Button";
import AlertDialog from "../AlertDialog/AlertDialog";
import EntitySearchInput from "../EntitySearchInput/EntitySearchInput";
import styles from "./ActivityInput.module.scss";
import { useActivityInput } from "./useActivityInput";
import SupportFlowModal from "../SupportFlow/SupportFlowModal";

function PlayIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false" width="1em" height="1em">
      <path d="M8 5.5v13a1 1 0 0 0 1.53.85l10.4-6.5a1 1 0 0 0 0-1.7l-10.4-6.5A1 1 0 0 0 8 5.5Z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false" width="1em" height="1em">
      <rect x="6" y="6" width="12" height="12" rx="1.5" />
    </svg>
  );
}

export default function ActivityInput() {
  const {
    name,
    setName,
    isActive,
    inputValue,
    formattedLimit,
    showAutoStopWarning,
    flowState,
    flowDispatch,
    handleConfirmActivity,
    handleToggle,
    handleSelectActivity,
    handleCreateActivity,
    submitAndOpenSupport,
    openSupportMode,
    defaultEntries,
  } = useActivityInput();

  const [submitConfirmOpen, setSubmitConfirmOpen] = useState(false);

  return (
    <>
      <div className={styles.containerOuter}>
        <div
          className={classNames(styles.container, {
            [styles.isRunning]: isActive,
            [styles.needsAttention]: !isActive,
          })}
        >
          <div className={styles.row}>
            <div className={styles.grow}>
              <EntitySearchInput
                type="activity"
                value={inputValue}
                onChange={setName}
                onSelect={async (activity) => {
                  await handleSelectActivity(activity);
                }}
                onCreate={async (activityName) => {
                  await handleCreateActivity(activityName);
                }}
                placeholder="Start typing, or choose from the list below"
                ariaLabel="Activity name"
                className={styles.entitySearch}
                inputClassName={classNames(styles.inputText, {
                  [styles.inputCTA]: !isActive,
                  [styles.inputMuted]: isActive,
                })}
                searchEnabled={!isActive}
                alwaysOpen={!isActive}
                defaultResults={defaultEntries}
                emptyMessage="No recent activities or tasks yet — type above to start something new."
              />
            </div>

            <Button
              onClick={handleToggle}
              variant="primary"
              className={classNames(styles.ctaButton, styles.control)}
              icon={isActive ? <StopIcon /> : <PlayIcon />}
            >
              {isActive ? "Stop" : "Start"}
            </Button>
          </div>

        </div>

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

      </div>

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
