import React, { useEffect } from "react";

import Button from "../Button/Button";
import Input from "../Input/Input";
import List from "../List/List";
import Modal from "../Modal/Modal";
import { useNotesPanel } from "./useNotesPanel";
import styles from "./NotesPanel.module.scss";

function bodyPreview(body: string): string {
  const trimmed = body.trim();
  if (trimmed.length <= 140) return trimmed;
  return `${trimmed.slice(0, 140)}…`;
}

interface NotesPanelProps {
  /** Called with a task id when the user clicks a note's linked-task link. */
  onOpenTask?: (taskId: number) => void;
  /** Opens the edit modal for this note id once the notes have loaded. */
  openNoteId?: number | null;
  /** Called once the requested `openNoteId` has been opened, so the caller can clear it. */
  onOpenNoteHandled?: () => void;
}

export default function NotesPanel({
  onOpenTask,
  openNoteId,
  onOpenNoteHandled,
}: NotesPanelProps = {}): React.ReactElement | null {
  const {
    isLoading,
    visibleNotes,
    getTaskName,
    newTitle,
    setNewTitle,
    newBody,
    setNewBody,
    handleCreate,
    activeNote,
    editTitle,
    setEditTitle,
    editBody,
    setEditBody,
    confirmingDelete,
    openNote,
    closeNote,
    handleEditSave,
    handleDeleteRequest,
    cancelDeleteRequest,
    handleDeleteConfirm,
  } = useNotesPanel();

  // Deep-link support: open a specific note's edit modal (e.g. navigated to
  // from a task's "View linked note" link) once it's available in `visibleNotes`.
  useEffect(() => {
    if (openNoteId == null) return;

    const note = visibleNotes.find((n) => n.id === openNoteId);
    if (!note) return;

    openNote(note);
    onOpenNoteHandled?.();
  }, [openNoteId, visibleNotes, openNote, onOpenNoteHandled]);

  const handleLinkedTaskClick = () => {
    if (activeNote?.task === null || activeNote?.task === undefined) return;
    const taskId = activeNote.task;
    closeNote();
    onOpenTask?.(taskId);
  };

  if (isLoading) return <p>Loading notes...</p>;

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <form className={styles.addNoteForm} onSubmit={handleCreate}>
          <Input
            id="new-note-title"
            value={newTitle}
            onChange={(v) => setNewTitle(v as string)}
            placeholder="New note title"
            className={styles.addNoteTitleInput}
          />
          <textarea
            aria-label="new note body"
            className={styles.addNoteBodyInput}
            value={newBody}
            onChange={(e) => setNewBody(e.target.value)}
            placeholder="Note content (optional)"
            rows={2}
          />
          <Button type="submit">Add note</Button>
        </form>

        <div className={styles.notesList}>
          {visibleNotes.length > 0 ? (
            <List
              items={visibleNotes}
              ariaLabel="Notes"
              canHover
              className={styles.list}
              sectionClass={styles.section}
              renderItem={(note) => {
                const linkedTaskName = getTaskName(note.task);
                return (
                  <button
                    type="button"
                    className={styles.noteButton}
                    aria-label={`Open note ${note.title}`}
                    onClick={() => openNote(note)}
                  >
                    <div className={styles.noteDetails}>
                      <div className={styles.noteTitle}>{note.title}</div>
                      {note.body ? (
                        <div className={styles.noteMeta}>{bodyPreview(note.body)}</div>
                      ) : null}
                      {linkedTaskName ? (
                        <div className={styles.noteMeta}>Linked task: {linkedTaskName}</div>
                      ) : null}
                    </div>
                  </button>
                );
              }}
            />
          ) : (
            <div className={styles.emptyState}>
              <p>No notes yet.</p>
            </div>
          )}
        </div>
      </div>

      {activeNote ? (
        <Modal
          id="edit-note-modal"
          title={confirmingDelete ? "Delete note?" : "Edit note"}
          onClose={closeNote}
          onBack={confirmingDelete ? cancelDeleteRequest : undefined}
          backLabel="Back"
        >
          {confirmingDelete ? (
            <div className={styles.deleteConfirmContent}>
              <p>
                Are you sure you want to delete
                {activeNote.title ? ` "${activeNote.title}"` : " this note"}?
              </p>
              <div className={styles.deleteConfirmActions}>
                <Button variant="secondary" onClick={closeNote}>
                  Cancel
                </Button>
                <Button variant="danger" onClick={handleDeleteConfirm}>
                  Delete
                </Button>
              </div>
            </div>
          ) : (
            <div className={styles.editContent}>
              <Input
                id="edit-note-title"
                label="Title"
                value={editTitle}
                onChange={(v) => setEditTitle(v as string)}
              />
              <label className={styles.bodyLabel} htmlFor="edit-note-body">
                Body
              </label>
              <textarea
                id="edit-note-body"
                className={styles.editBodyInput}
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
                rows={6}
              />
              {activeNote.task !== null ? (
                <div className={styles.noteMeta}>
                  Linked task:{" "}
                  {onOpenTask ? (
                    <button
                      type="button"
                      className={styles.linkedTaskLink}
                      onClick={handleLinkedTaskClick}
                    >
                      {getTaskName(activeNote.task)}
                    </button>
                  ) : (
                    getTaskName(activeNote.task)
                  )}
                </div>
              ) : null}
              <div className={styles.editActions}>
                <Button variant="primary" onClick={handleEditSave}>
                  Save
                </Button>
                <Button variant="secondary" onClick={closeNote}>
                  Cancel
                </Button>
                <Button variant="secondaryDanger" onClick={handleDeleteRequest}>
                  Delete
                </Button>
              </div>
            </div>
          )}
        </Modal>
      ) : null}
    </div>
  );
}
