import { useCallback, useMemo, useState } from "react";
import classNames from "classnames";

import Button from "../Button/Button";
import List from "../List/List";
import Modal from "../Modal/Modal";
import styles from "./PlayerItemList.module.scss";

export default function PlayerItemList({
  items = [],
  itemLabel = "item",
  ariaLabel,
  getItemName = (item) => item?.name ?? "",
  isItemComplete,
  onToggleComplete,
  getItemKey,
  renderItemMeta,
  renderEditSummary,
  onEdit,
  onDelete,
  listClassName,
  sectionClassName,
}) {
  const [activeItem, setActiveItem] = useState(null);
  const [editingName, setEditingName] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const itemLabelLower = itemLabel.toLowerCase();
  const canToggleComplete = typeof onToggleComplete === "function";
  const canEdit = typeof onEdit === "function";
  const canDelete = typeof onDelete === "function";

  const activeItemName = activeItem ? getItemName(activeItem) : "";
  const modalSummary = activeItem
    ? (renderEditSummary?.(activeItem) ?? renderItemMeta?.(activeItem) ?? null)
    : null;

  const handleOpenItem = useCallback(
    (item) => {
      setActiveItem(item);
      setEditingName(getItemName(item));
    },
    [getItemName],
  );

  const handleModalClose = useCallback(() => {
    setActiveItem(null);
    setEditingName("");
    setConfirmingDelete(false);
  }, []);

  const handleEditSave = useCallback(() => {
    if (!activeItem || !canEdit) {
      return;
    }

    const trimmedName = editingName.trim();
    if (!trimmedName) {
      return;
    }

    onEdit(activeItem, trimmedName);
    handleModalClose();
  }, [activeItem, canEdit, editingName, handleModalClose, onEdit]);

  const handleDeleteRequest = useCallback(() => {
    setConfirmingDelete(true);
  }, []);

  const handleDeleteConfirm = useCallback(() => {
    if (!activeItem || !canDelete) {
      return;
    }
    onDelete(activeItem);
    handleModalClose();
  }, [activeItem, canDelete, handleModalClose, onDelete]);

  const modalIdPrefix = useMemo(
    () => itemLabelLower.replace(/\s+/g, "-"),
    [itemLabelLower],
  );

  return (
    <>
      <List
        items={items}
        ariaLabel={ariaLabel}
        canHover
        className={classNames(styles.list, listClassName)}
        sectionClass={classNames(styles.section, sectionClassName)}
        getKey={getItemKey}
        getItemClassName={(item) =>
          classNames(styles.item, {
            [styles.itemCompleted]: isItemComplete?.(item),
          })
        }
        renderItem={(item) => (
          <>
            {canToggleComplete ? (
              <label className={styles.completeCheckboxLabel}>
                <input
                  className={styles.completeCheckbox}
                  type="checkbox"
                  checked={Boolean(isItemComplete?.(item))}
                  onChange={() => onToggleComplete(item)}
                    aria-label={`Mark ${getItemName(item) || itemLabelLower} as complete`}
                  />
                </label>
              ) : null}
            <button
              type="button"
              className={styles.itemButton}
              aria-label={`Open ${itemLabelLower} ${getItemName(item)}`}
              onClick={() => handleOpenItem(item)}
            >
              <div className={styles.itemDetails}>
                <div className={styles.itemName}>{getItemName(item)}</div>
                {renderItemMeta ? (
                  <div className={styles.itemMeta}>{renderItemMeta(item)}</div>
                ) : null}
              </div>
            </button>
          </>
        )}
      />

      {activeItem ? (
        <Modal
          id={`edit-${modalIdPrefix}-modal`}
          title={
            confirmingDelete
              ? `Delete ${itemLabelLower}?`
              : activeItemName || `Edit ${itemLabelLower}`
          }
          onClose={handleModalClose}
          onBack={confirmingDelete ? () => setConfirmingDelete(false) : undefined}
          backLabel="Back"
        >
          {confirmingDelete ? (
            <div className={styles.deleteConfirmContent}>
              <p>
                Are you sure you want to delete
                {activeItemName ? ` "${activeItemName}"` : ` this ${itemLabelLower}`}?
              </p>
              <div className={styles.deleteConfirmActions}>
                <Button variant="secondary" onClick={() => setConfirmingDelete(false)}>
                  Cancel
                </Button>
                <Button variant="danger" onClick={handleDeleteConfirm}>
                  Delete
                </Button>
              </div>
            </div>
          ) : (
            <div className={styles.editConfirmContent}>
              {canEdit ? (
                <input
                  type="text"
                  className={styles.editInput}
                  aria-label={`${itemLabel} name`}
                  value={editingName}
                  onChange={(event) => setEditingName(event.target.value)}
                  autoFocus
                  onKeyDown={(event) => {
                    if (event.key === "Enter") handleEditSave();
                    if (event.key === "Escape") handleModalClose();
                  }}
                />
              ) : null}
              {modalSummary ? (
                <p className={styles.editConfirmMeta}>{modalSummary}</p>
              ) : null}
              <div className={styles.editConfirmActions}>
                {canEdit ? (
                  <Button variant="primary" onClick={handleEditSave}>
                    Save
                  </Button>
                ) : null}
                <Button variant="secondary" onClick={handleModalClose}>
                  {canEdit ? "Cancel" : "Close"}
                </Button>
                {canDelete ? (
                  <Button variant="secondaryDanger" onClick={handleDeleteRequest}>
                    Delete
                  </Button>
                ) : null}
              </div>
            </div>
          )}
        </Modal>
      ) : null}
    </>
  );
}
