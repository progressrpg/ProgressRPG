import { useCallback, useMemo, useRef, useState } from "react";

import { useSaveStatus, type SaveStatusHelpers } from "./useSaveStatus";

export interface SaveCallbacks {
  onSuccess?: () => void;
  onError?: () => void;
}

interface UsePlayerItemModalProps<T extends { id?: string | number; name?: string }> {
  items: T[];
  getItemName: (item: T) => string;
  renderItemMeta?: (item: T) => React.ReactNode;
  renderEditSummary?: (item: T, saveHelpers: SaveStatusHelpers) => React.ReactNode;
  onEdit?: (item: T, name: string, callbacks?: SaveCallbacks) => void;
  onDelete?: (item: T) => void;
}

export function usePlayerItemModal<T extends { id?: string | number; name?: string }>({
  items,
  getItemName,
  renderItemMeta,
  renderEditSummary,
  onEdit,
  onDelete,
}: UsePlayerItemModalProps<T>) {
  const [activeItem, setActiveItem] = useState<T | null>(null);
  const [editingName, setEditingName] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  // Tracks the last name we've committed (or started committing) a save
  // for, so blur/Enter only fire a request when the name actually changed.
  const lastSavedNameRef = useRef("");

  const { saveStatus, reportSaving, reportSaved, reportError, resetSaveStatus } = useSaveStatus();

  const handleOpenItem = useCallback(
    (item: T) => {
      setActiveItem(item);
      const name = getItemName(item);
      setEditingName(name);
      lastSavedNameRef.current = name;
      resetSaveStatus();
    },
    [getItemName, resetSaveStatus],
  );

  const handleModalClose = useCallback(() => {
    setActiveItem(null);
    setEditingName("");
    setConfirmingDelete(false);
    resetSaveStatus();
  }, [resetSaveStatus]);

  // Autosaves the name field. Fires on blur (and Enter) rather than on
  // every keystroke, mirroring the due-date field's commit-on-blur pattern.
  const commitNameEdit = useCallback(() => {
    if (!activeItem || !onEdit) {
      return;
    }

    const trimmedName = editingName.trim();
    if (!trimmedName || trimmedName === lastSavedNameRef.current) {
      return;
    }

    lastSavedNameRef.current = trimmedName;
    reportSaving();
    onEdit(activeItem, trimmedName, {
      onSuccess: reportSaved,
      onError: reportError,
    });
  }, [activeItem, editingName, onEdit, reportSaving, reportSaved, reportError]);

  // handleEditSave is kept as the exported name for the commit action
  // (bound to the name input's blur/Enter handlers) since it's still the
  // thing that saves the edit — there's just no explicit "Save" button
  // triggering it anymore.
  const handleEditSave = commitNameEdit;

  const handleDeleteRequest = useCallback(() => {
    setConfirmingDelete(true);
  }, []);

  const handleDeleteConfirm = useCallback(() => {
    if (!activeItem || !onDelete) {
      return;
    }

    onDelete(activeItem);
    handleModalClose();
  }, [activeItem, onDelete, handleModalClose]);

  // Keep dialog state in sync with the live items array so toggling
  // complete outside the dialog is reflected immediately.
  const liveActiveItem = useMemo(
    () =>
      activeItem
        ? (
            items.find(
              (item) =>
                item.id !== undefined && item.id === activeItem.id,
            ) ?? activeItem
          )
        : null,
    [activeItem, items],
  );

  const activeItemName = useMemo(
    () => (liveActiveItem ? getItemName(liveActiveItem) : ""),
    [liveActiveItem, getItemName],
  );

  const saveHelpers = useMemo<SaveStatusHelpers>(
    () => ({ reportSaving, reportSaved, reportError }),
    [reportSaving, reportSaved, reportError],
  );

  const modalSummary = useMemo(() => {
    if (!liveActiveItem) {
      return null;
    }

    return (
      renderEditSummary?.(liveActiveItem, saveHelpers) ??
      renderItemMeta?.(liveActiveItem) ??
      null
    );
  }, [liveActiveItem, renderEditSummary, renderItemMeta, saveHelpers]);

  return {
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
  };
}
