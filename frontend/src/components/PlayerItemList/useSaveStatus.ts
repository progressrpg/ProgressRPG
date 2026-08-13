import { useCallback, useEffect, useRef, useState } from "react";

export type SaveStatus = "idle" | "saving" | "saved" | "error";

export interface SaveStatusHelpers {
  reportSaving: () => void;
  reportSaved: () => void;
  reportError: () => void;
}

const SAVED_DISPLAY_MS = 2500;

/**
 * Tracks a single in-flight autosave's status so a modal can show a brief
 * "Saved"/"Couldn't save" indicator. "saved" auto-clears after a few
 * seconds; "error" persists until the next save attempt or a manual reset,
 * since a missed save is worse than a lingering banner.
 */
export function useSaveStatus() {
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearHideTimer = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  const reportSaving = useCallback(() => {
    clearHideTimer();
    setSaveStatus("saving");
  }, [clearHideTimer]);

  const reportSaved = useCallback(() => {
    clearHideTimer();
    setSaveStatus("saved");
    hideTimerRef.current = setTimeout(() => setSaveStatus("idle"), SAVED_DISPLAY_MS);
  }, [clearHideTimer]);

  const reportError = useCallback(() => {
    clearHideTimer();
    setSaveStatus("error");
  }, [clearHideTimer]);

  const resetSaveStatus = useCallback(() => {
    clearHideTimer();
    setSaveStatus("idle");
  }, [clearHideTimer]);

  useEffect(() => clearHideTimer, [clearHideTimer]);

  return { saveStatus, reportSaving, reportSaved, reportError, resetSaveStatus };
}
