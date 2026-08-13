import React, { useEffect, useMemo } from "react";
import classNames from "classnames";

import Button from "../Button/Button";
import List from "../List/List";
import Modal from "../Modal/Modal";
import SaveStatusIndicator from "./SaveStatusIndicator";
import { usePlayerItemListControls } from "./usePlayerItemListControls";
import { usePlayerItemModal } from "./usePlayerItemModal";
import type { SaveCallbacks } from "./usePlayerItemModal";
import type { SaveStatusHelpers } from "./useSaveStatus";
import styles from "./PlayerItemList.module.scss";

export interface SortOption<T> {
  key: string;
  label: string;
  compareFn: (a: T, b: T) => number;
}

export interface FilterOption<T> {
  key: string;
  label: string;
  predicate: (item: T) => boolean;
}

interface PlayerItemListProps<T extends { id?: string | number; name?: string }> {
  items?: T[];
  itemLabel?: string;
  ariaLabel?: string;
  getItemName?: (item: T) => string;
  isItemComplete?: (item: T) => boolean;
  onToggleComplete?: (item: T) => void;
  getItemKey?: (item: T, index: number) => string | number;
  renderItemMeta?: (item: T) => React.ReactNode;
  renderEditSummary?: (item: T, saveHelpers: SaveStatusHelpers) => React.ReactNode;
  onEdit?: (item: T, name: string, callbacks?: SaveCallbacks) => void;
  onDelete?: (item: T) => void;
  hoverEdit?: boolean;
  renderRowActions?: (item: T) => React.ReactNode;
  listClassName?: string;
  sectionClassName?: string;
  sortOptions?: SortOption<T>[];
  filterOptions?: FilterOption<T>[];
  controls?: React.ReactNode;
  /** When set, opens the edit modal for the item with this id (e.g. deep-linked from another panel). */
  openItemId?: string | number | null;
  /** Called once the requested `openItemId` has been opened, so the caller can clear it. */
  onOpenItemHandled?: () => void;
  getChildren?: (item: T) => T[] | undefined;
}

export default function PlayerItemList<T extends { id?: string | number; name?: string }>({
  items = [],
  itemLabel = "item",
  ariaLabel,
  getItemName = (item) => (item?.name ?? "") as string,
  isItemComplete,
  onToggleComplete,
  getItemKey,
  renderItemMeta,
  renderEditSummary,
  onEdit,
  onDelete,
  hoverEdit = false,
  renderRowActions,
  listClassName,
  sectionClassName,
  sortOptions,
  filterOptions,
  controls,
  openItemId,
  onOpenItemHandled,
  getChildren,
}: PlayerItemListProps<T>) {
  const {
    activeFilterKey,
    setActiveFilterKey,
    activeSortKey,
    setActiveSortKey,
    itemLabelLower,
    modalIdPrefix,
    displayItems,
    hasControls,
  } = usePlayerItemListControls({
    items,
    itemLabel,
    filterOptions,
    sortOptions,
    controls,
  });

  const {
    activeItem,
    liveActiveItem,
    editingName,
    confirmingDelete,
    saveStatus,
    activeItemName,
    modalSummary,
    setEditingName,
    setConfirmingDelete,
    handleOpenItem,
    handleModalClose,
    handleEditSave,
    handleDeleteRequest,
    handleDeleteConfirm,
  } = usePlayerItemModal({
    items,
    getItemName,
    renderItemMeta,
    renderEditSummary,
    onEdit,
    onDelete,
  });

  // Deep-link support: open a specific item's edit modal (e.g. navigated to
  // from another panel) once its data is available in `items`.
  useEffect(() => {
    if (openItemId === null || openItemId === undefined) return;

    const item = items.find((i) => i.id !== undefined && i.id === openItemId);
    if (!item) return;

    handleOpenItem(item);
    onOpenItemHandled?.();
  }, [openItemId, items, handleOpenItem, onOpenItemHandled]);

  const canToggleComplete = typeof onToggleComplete === "function";
  const canEdit = typeof onEdit === "function";
  const canDelete = typeof onDelete === "function";

  const childIds = useMemo(() => {
    const ids = new Set<string | number>();
    if (!getChildren) return ids;
    items.forEach((item) => {
      getChildren(item)?.forEach((child) => {
        if (child.id !== undefined) ids.add(child.id);
      });
    });
    return ids;
  }, [items, getChildren]);

  // Sort/filter controls only apply to top-level items; a child keeps its
  // place directly after its parent (in `getChildren`'s order) rather than
  // being reordered independently.
  const flatDisplayItems = useMemo(() => {
    if (!getChildren) return displayItems;
    const topLevel = displayItems.filter(
      (item) => item.id === undefined || !childIds.has(item.id)
    );
    return topLevel.flatMap((item) => [item, ...(getChildren(item) ?? [])]);
  }, [displayItems, getChildren, childIds]);

  const renderRow = (item: T): React.ReactNode => (
    <>
      {canToggleComplete ? (
        <label className={styles.completeCheckboxLabel}>
          <input
            className={styles.completeCheckbox}
            type="checkbox"
            checked={Boolean(isItemComplete?.(item))}
            onChange={() => onToggleComplete!(item)}
            aria-label={`Mark ${getItemName(item) || itemLabelLower} as complete`}
          />
        </label>
      ) : null}
      {hoverEdit ? (
        <div className={styles.itemContent}>
          {canEdit ? (
            <button
              type="button"
              className={classNames(styles.itemDetails, styles.itemDetailsButton)}
              aria-label={`Edit ${itemLabelLower} ${getItemName(item)}`}
              onClick={() => handleOpenItem(item)}
            >
              <div className={styles.itemName}>{getItemName(item)}</div>
              {renderItemMeta ? (
                <div className={styles.itemMeta}>{renderItemMeta(item)}</div>
              ) : null}
            </button>
          ) : (
            <div className={styles.itemDetails}>
              <div className={styles.itemName}>{getItemName(item)}</div>
              {renderItemMeta ? (
                <div className={styles.itemMeta}>{renderItemMeta(item)}</div>
              ) : null}
            </div>
          )}
          <div className={styles.rowActions}>
            {renderRowActions?.(item)}
            {canEdit ? (
              <button
                type="button"
                className={styles.editHoverButton}
                aria-label={`Edit ${itemLabelLower} ${getItemName(item)}`}
                onClick={() => handleOpenItem(item)}
              >
                📝
              </button>
            ) : null}
          </div>
        </div>
      ) : (
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
      )}
    </>
  );

  return (
    <div className={styles.wrapper}>
      {hasControls ? (
        <div className={styles.controls}>
          {controls ?? null}
          {filterOptions?.length ? (
            <div className={styles.controlGroup} role="group" aria-label={`Filter ${itemLabelLower}s`}>
              {filterOptions.map((opt) => (
                <Button
                  key={opt.key}
                  variant={activeFilterKey === opt.key ? "primary" : "secondary"}
                  onClick={() => setActiveFilterKey(opt.key)}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          ) : null}
          {sortOptions?.length ? (
            <div className={styles.controlGroup}>
              <label className={styles.controlLabel} htmlFor={`${modalIdPrefix}-sort`}>
                Sort:
              </label>
              <select
                id={`${modalIdPrefix}-sort`}
                className={styles.sortSelect}
                value={activeSortKey ?? ""}
                onChange={(e) => setActiveSortKey(e.target.value)}
              >
                {sortOptions.map((opt) => (
                  <option key={opt.key} value={opt.key}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
        </div>
      ) : null}
      <div className={styles.listScroll}>
      <List
        items={flatDisplayItems}
        ariaLabel={ariaLabel}
        canHover
        className={classNames(styles.list, listClassName)}
        sectionClass={classNames(styles.section, sectionClassName)}
        getKey={getItemKey}
        getItemClassName={(item) =>
          classNames(styles.item, {
            [styles.childItem]: item.id !== undefined && childIds.has(item.id),
            [styles.itemCompleted]: isItemComplete?.(item),
          })
        }
        renderItem={(item) => renderRow(item)}
      />
      </div>

      {activeItem ? (
        <Modal
          id={`edit-${modalIdPrefix}-modal`}
          title={
            confirmingDelete
              ? `Delete ${itemLabelLower}?`
              : `Edit ${itemLabelLower}`
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
              {(canToggleComplete || canEdit) ? (
                <div className={styles.editTitleRow}>
                  {canToggleComplete && liveActiveItem ? (
                    <label className={styles.completeCheckboxLabel}>
                      <input
                        className={styles.completeCheckbox}
                        type="checkbox"
                        checked={Boolean(isItemComplete?.(liveActiveItem))}
                        onChange={() => onToggleComplete!(liveActiveItem)}
                        aria-label={`Mark ${activeItemName || itemLabelLower} as complete`}
                      />
                    </label>
                  ) : null}
                  {canEdit ? (
                    <input
                      type="text"
                      className={styles.editInput}
                      aria-label={`${itemLabel} name`}
                      value={editingName}
                      onChange={(event) => setEditingName(event.target.value)}
                      onBlur={handleEditSave}
                      autoFocus
                      onKeyDown={(event) => {
                        if (event.key === "Enter") handleEditSave();
                        if (event.key === "Escape") handleModalClose();
                      }}
                    />
                  ) : null}
                </div>
              ) : null}
              {modalSummary ? (
                <div className={styles.editConfirmMeta}>{modalSummary}</div>
              ) : null}
              <div className={styles.editConfirmActions}>
                <Button variant="secondary" onClick={handleModalClose}>
                  Close
                </Button>
                {canDelete ? (
                  <Button variant="secondaryDanger" onClick={handleDeleteRequest}>
                    Delete
                  </Button>
                ) : null}
                <SaveStatusIndicator status={saveStatus} />
              </div>
            </div>
          )}
        </Modal>
      ) : null}
    </div>
  );
}
