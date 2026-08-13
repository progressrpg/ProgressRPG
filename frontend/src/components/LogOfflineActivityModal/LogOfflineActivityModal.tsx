import classNames from "classnames";

import Modal from "../Modal/Modal";
import Button from "../Button/Button";
import Input from "../Input/Input";
import EntitySearchInput from "../EntitySearchInput/EntitySearchInput";
import { formatDurationShort } from "../../utils/formatUtils";
import { useLogOfflineActivityForm } from "./useLogOfflineActivityForm";
import styles from "./LogOfflineActivityModal.module.scss";

interface LogOfflineActivityModalProps {
  onClose: () => void;
}

export default function LogOfflineActivityModal({ onClose }: LogOfflineActivityModalProps) {
  const {
    taskName,
    handleTaskNameChange,
    handleTaskSelect,
    durationHours,
    setDurationHours,
    durationMinutes,
    setDurationMinutes,
    totalDurationMinutes,
    completionDate,
    handleCompletionDateChange,
    completionTime,
    handleCompletionTimeChange,
    maxCompletionDate,
    fieldErrors,
    submitError,
    result,
    eligibility,
    isSubmitting,
    handleSubmit,
    reset,
  } = useLogOfflineActivityForm();

  if (result) {
    return (
      <Modal title="Activity logged" onClose={onClose} size="sm">
        <div className={styles.confirmation}>
          <p className={styles.confirmationHeadline}>
            &ldquo;{result.activity.name}&rdquo; has been recorded.
          </p>
          {result.xp_gained > 0 ? (
            <p className={classNames(styles.eligibilityBanner, styles.success)}>
              +{result.xp_gained} XP awarded
            </p>
          ) : (
            <p className={classNames(styles.eligibilityBanner, styles.info)}>
              No XP was awarded for this activity.
            </p>
          )}
          <div className={styles.confirmationActions}>
            <Button variant="secondary" onClick={reset}>
              Log another
            </Button>
            <Button onClick={onClose}>Done</Button>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title="Log offline activity" onClose={onClose} size="sm">
      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.field}>
          <span className={styles.label}>
            Task <span className={styles.required} aria-label="required">*</span>
          </span>
          <EntitySearchInput
            type="task"
            value={taskName}
            onChange={handleTaskNameChange}
            onSelect={handleTaskSelect}
            placeholder="Search or enter a task name"
            ariaLabel="Task"
            inputClassName={styles.taskInput}
          />
          {fieldErrors.task && (
            <p className={styles.errorText} role="alert">{fieldErrors.task}</p>
          )}
        </div>

        <div className={styles.field}>
          <span className={styles.label}>
            Duration <span className={styles.required} aria-label="required">*</span>
          </span>
          <div className={styles.row}>
            <Input
              id="offline-activity-duration-hours"
              ariaLabel="Hours"
              type="number"
              placeholder="hh"
              value={durationHours}
              onChange={(value) => setDurationHours(value as string)}
              className={styles.durationPartField}
            />
            <Input
              id="offline-activity-duration-minutes"
              ariaLabel="Minutes"
              type="number"
              placeholder="mm"
              value={durationMinutes}
              onChange={(value) => setDurationMinutes((value as string).slice(0, 2))}
              maxLength={2}
              className={styles.durationPartField}
            />
          </div>
          {fieldErrors.duration && (
            <p className={styles.errorText} role="alert">{fieldErrors.duration}</p>
          )}
        </div>

        <div className={styles.field}>
          <span className={styles.label}>Completed</span>
          <div className={styles.row}>
            <Input
              id="offline-activity-date"
              ariaLabel="Completion date"
              type="date"
              value={completionDate}
              onChange={(value) => handleCompletionDateChange(value as string)}
              max={maxCompletionDate}
            />
            <Input
              id="offline-activity-time"
              ariaLabel="Completion time"
              type="time"
              value={completionTime}
              onChange={(value) => handleCompletionTimeChange(value as string)}
            />
          </div>
          {fieldErrors.completedAt && (
            <p className={styles.errorText} role="alert">{fieldErrors.completedAt}</p>
          )}
        </div>

        {!Number.isNaN(totalDurationMinutes) && totalDurationMinutes > 0 && (
          <p className={styles.durationPreview}>
            Logging {formatDurationShort(Math.round(totalDurationMinutes * 60))}
          </p>
        )}

        {eligibility && (
          <p
            className={classNames(styles.eligibilityBanner, styles[eligibility.tone])}
            role="status"
          >
            {eligibility.message}
          </p>
        )}

        {submitError && (
          <p className={styles.errorText} role="alert">{submitError}</p>
        )}

        <div className={styles.actions}>
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Logging…" : "Log activity"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
