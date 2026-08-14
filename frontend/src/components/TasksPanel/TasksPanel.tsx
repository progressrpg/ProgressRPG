import React, { useRef } from "react";
import classNames from "classnames";

import EntitySearchInput from "../EntitySearchInput/EntitySearchInput";
import Button from "../Button/Button";
import PlayerItemList from "../PlayerItemList/PlayerItemList";
import Tooltip from "../Tooltip/Tooltip";
import { isTaskComplete, taskSortOptions, useTasksPanel, type ItemRecord } from "./useTasksPanel";
import { toDateInputValue, toTimeInputValue, fromDateAndTimeInputValues } from "../../utils/formatUtils";
import styles from "./TasksPanel.module.scss";

interface TasksPanelProps {
  /** Opens the edit modal for this task id once the tasks have loaded. */
  openTaskId?: number | null;
  /** Called once the requested `openTaskId` has been opened, so the caller can clear it. */
  onOpenTaskHandled?: () => void;
  /** Called with a note id when the user creates or opens a task's linked note. */
  onOpenNote?: (noteId: number) => void;
}

export default function TasksPanel({
  openTaskId,
  onOpenTaskHandled,
  onOpenNote,
}: TasksPanelProps = {}): React.ReactElement | null {
  const {
    isLoading,
    newName,
    setNewName,
    hideCompleted,
    visibleTasks,
    getChildren,
    topLevelTasks,
    pendingOpenTaskId,
    hiddenItemIds,
    startAddSubtask,
    clearPendingOpenTaskId,
    discardDraftTask,
    handleCreateTask,
    handleSubmitForm,
    handleEdit,
    handleDelete,
    handleToggleComplete,
    handleStartTask,
    toggleHideCompleted,
    getTaskMeta,
    getTaskEditSummary,
    getLinkedNoteId,
    handleCreateNoteForTask,
    updateTask,
  } = useTasksPanel(openTaskId, onOpenNote);

  // Only one task's edit summary is ever open at a time (it renders inside a modal), so a
  // single pair of refs is enough to read the sibling input's value when committing due_at.
  const dueDateInputRef = useRef<HTMLInputElement>(null);
  const dueTimeInputRef = useRef<HTMLInputElement>(null);

  if (isLoading) return <p>Loading tasks...</p>;

  return (
    <div className={styles.page}>
      <div className={styles.content}>
      <form className={styles.addTaskForm} onSubmit={handleSubmitForm}>
        <EntitySearchInput
          type="task"
          value={newName}
          onChange={(v) => setNewName(v)}
          onCreate={(name) => handleCreateTask(name)}
          placeholder="New task name"
          className={styles.addTaskInput}
        />
        <Button type="submit">
          <span className={styles.addButtonText}>Add task</span>
          <span className={styles.addButtonIcon} aria-hidden="true">✓</span>
        </Button>
      </form>

      <div className={styles.tasksList}>
        <PlayerItemList<ItemRecord>
          items={visibleTasks as ItemRecord[]}
          getChildren={getChildren}
          itemLabel="task"
          ariaLabel="Tasks"
          isItemComplete={isTaskComplete}
          onToggleComplete={handleToggleComplete}
          renderItemMeta={(task) => {
            const meta = getTaskMeta(task);
            return (
              <>
                {meta.lastWorkedOn}
                {meta.completionXp ? <> • +{meta.completionXp} XP</> : null}
                {task.due_at ? (
                  <>
                    {" "}
                    •{" "}
                    <span className={classNames({ [styles.overdue]: meta.isOverdue })}>
                      Due {meta.dueAt}
                    </span>
                  </>
                ) : null}
              </>
            );
          }}
          renderEditSummary={(taskItem, saveHelpers) => {
            if (taskItem.id < 0) {
              // An unsaved draft subtask: nothing to show or edit here yet
              // (due date, parent, notes) until it's actually been created.
              return <div className={styles.timestampLabel}>Type a name to create this subtask.</div>;
            }

            const summary = getTaskEditSummary(taskItem);
            const hasSubtasks = (taskItem.subtask_count ?? 0) > 0;
            const parentOptions = topLevelTasks.filter((t) => t.id !== taskItem.id);
            const parentTask = topLevelTasks.find((t) => t.id === taskItem.parent) ?? null;

            return (
              <>
                <div>
                  Total time: {summary.totalTime}
                </div>
                {onOpenNote ? (
                  (() => {
                    const linkedNoteId = getLinkedNoteId(taskItem);
                    return linkedNoteId !== null ? (
                      <button
                        type="button"
                        className={styles.linkedNoteLink}
                        onClick={() => onOpenNote(linkedNoteId)}
                      >
                        View linked note
                      </button>
                    ) : (
                      <Button
                        variant="secondary"
                        onClick={() => handleCreateNoteForTask(taskItem)}
                      >
                        Create note for this task
                      </Button>
                    );
                  })()
                ) : null}
                <div className={styles.dueDateRow}>
                  <label className={styles.timestampLabel} htmlFor="task-due-at-date">
                    Due date
                  </label>
                  <input
                    id="task-due-at-date"
                    ref={dueDateInputRef}
                    type="date"
                    className={styles.dueDateInput}
                    defaultValue={toDateInputValue(taskItem.due_at)}
                    onBlur={() => {
                      saveHelpers.reportSaving();
                      updateTask.mutate(
                        {
                          id: taskItem.id,
                          data: {
                            due_at: fromDateAndTimeInputValues(
                              dueDateInputRef.current?.value ?? "",
                              dueTimeInputRef.current?.value ?? "",
                            ),
                          },
                        },
                        { onSuccess: saveHelpers.reportSaved, onError: saveHelpers.reportError },
                      );
                    }}
                  />
                  <input
                    aria-label="Due time"
                    ref={dueTimeInputRef}
                    type="time"
                    className={styles.dueDateInput}
                    defaultValue={toTimeInputValue(taskItem.due_at)}
                    onBlur={() => {
                      if (dueTimeInputRef.current?.value && dueDateInputRef.current && !dueDateInputRef.current.value) {
                        dueDateInputRef.current.value = toDateInputValue(new Date().toISOString());
                      }
                      saveHelpers.reportSaving();
                      updateTask.mutate(
                        {
                          id: taskItem.id,
                          data: {
                            due_at: fromDateAndTimeInputValues(
                              dueDateInputRef.current?.value ?? "",
                              dueTimeInputRef.current?.value ?? "",
                            ),
                          },
                        },
                        { onSuccess: saveHelpers.reportSaved, onError: saveHelpers.reportError },
                      );
                    }}
                  />
                  {taskItem.due_at && (
                    <Button
                      variant="secondary"
                      onClick={() => {
                        if (dueDateInputRef.current) dueDateInputRef.current.value = "";
                        if (dueTimeInputRef.current) dueTimeInputRef.current.value = "";
                        saveHelpers.reportSaving();
                        updateTask.mutate(
                          { id: taskItem.id, data: { due_at: null } },
                          { onSuccess: saveHelpers.reportSaved, onError: saveHelpers.reportError },
                        );
                      }}
                    >
                      Clear
                    </Button>
                  )}
                </div>
                <div className={styles.parentRow}>
                  <label className={styles.timestampLabel} htmlFor="task-parent">
                    Parent task
                  </label>
                  {parentTask ? (
                    <span className={styles.parentChip}>
                      {parentTask.name}
                      <button
                        type="button"
                        className={styles.parentChipClear}
                        aria-label={`Remove parent task ${parentTask.name}`}
                        onClick={() => {
                          saveHelpers.reportSaving();
                          updateTask.mutate(
                            { id: taskItem.id, data: { parent: null } },
                            { onSuccess: saveHelpers.reportSaved, onError: saveHelpers.reportError },
                          );
                        }}
                      >
                        ×
                      </button>
                    </span>
                  ) : (
                    <Tooltip
                      content={
                        hasSubtasks
                          ? "This task already has subtasks and can't be nested under another task."
                          : undefined
                      }
                    >
                      <select
                        id="task-parent"
                        className={styles.parentSelect}
                        disabled={hasSubtasks}
                        defaultValue=""
                        onChange={(event) => {
                          saveHelpers.reportSaving();
                          updateTask.mutate(
                            {
                              id: taskItem.id,
                              data: { parent: event.target.value ? Number(event.target.value) : null },
                            },
                            { onSuccess: saveHelpers.reportSaved, onError: saveHelpers.reportError },
                          );
                        }}
                      >
                        <option value="">No parent</option>
                        {parentOptions.map((option) => (
                          <option key={option.id} value={option.id}>
                            {option.name}
                          </option>
                        ))}
                      </select>
                    </Tooltip>
                  )}
                </div>
              </>
            );
          }}
          renderTitleRowActions={(task) => {
            if (task.id < 0) return null;
            const summary = getTaskEditSummary(task);
            return (
              <Tooltip
                placement="bottom"
                align="end"
                content={
                  <div className={styles.taskTimestamps}>
                    <div>
                      <div className={styles.timestampLabel}>Created</div>
                      <div>{summary.created}</div>
                    </div>
                    <div>
                      <div className={styles.timestampLabel}>Modified</div>
                      <div>{summary.modified}</div>
                    </div>
                    <div>
                      <div className={styles.timestampLabel}>Completed</div>
                      <div>{summary.completed}</div>
                    </div>
                  </div>
                }
              >
                <button
                  type="button"
                  className={styles.timestampButton}
                  aria-label="View task timestamps"
                >
                  🕐
                </button>
              </Tooltip>
            );
          }}
          hoverEdit
          renderRowActions={(task) => (
            <>
              {task.parent == null && (
                <Tooltip content="Add a subtask">
                  <button
                    type="button"
                    className={styles.taskSubtaskButton}
                    aria-label={`Add subtask to ${task.name}`}
                    onClick={(event) => {
                      event.currentTarget.blur();
                      startAddSubtask(task);
                    }}
                  >
                    +
                  </button>
                </Tooltip>
              )}
              <Tooltip content="Start working on this task">
                <button
                  type="button"
                  className={styles.taskPlayButton}
                  aria-label={`Start working on ${task.name}`}
                  onClick={async (event) => {
                    event.currentTarget.blur();
                    await handleStartTask(task);
                  }}
                >
                  ▷
                </button>
              </Tooltip>
            </>
          )}
          onEdit={handleEdit}
          onDelete={handleDelete}
          openItemId={openTaskId ?? pendingOpenTaskId}
          onOpenItemHandled={() => {
            onOpenTaskHandled?.();
            clearPendingOpenTaskId();
          }}
          hiddenItemIds={hiddenItemIds}
          onModalClose={discardDraftTask}
          sortOptions={taskSortOptions}
          controls={
            <Button
              variant={hideCompleted ? "primary" : "secondary"}
              onClick={toggleHideCompleted}
              className={styles.filterToggle}
            >
              {hideCompleted ? "Show complete" : "Hide complete"}
            </Button>
          }
        />
        {visibleTasks.length === 0 && (
          <div className={styles.emptyState}>
            <p>{hideCompleted ? "No incomplete tasks." : "No tasks yet."}</p>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
