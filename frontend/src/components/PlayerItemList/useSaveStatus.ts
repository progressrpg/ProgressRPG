import { useCallback, useEffect, useRef, useState } from "react";

export type SaveStatus = "idle" | "saving" | "saved" | "error";

export interface SaveStatusHelpers {
  reportSaving: () => void;
  reportSaved: () => void;
  reportError: () => void;
}

const SAVED_DISPLAY_MS = 2500;
// Saves usually resolve fast enough that "Saving…" would just flash on
// screen; only show it once a save has been pending this long.
const SAVING_DISPLAY_DELAY_MS = 150;

/**
 * Tracks a single in-flight autosave's status so a modal can show a brief
 * "Saved"/"Couldn't save" indicator. "saved" auto-clears after a few
 * seconds; "error" persists until the next save attempt or a manual reset,
 * since a missed save is worse than a lingering banner.
 */
export function useSaveStatus() {
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const savingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearHideTimer = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  const clearSavingTimer = useCallback(() => {
    if (savingTimerRef.current) {
      clearTimeout(savingTimerRef.current);
      savingTimerRef.current = null;
    }
  }, []);

  const reportSaving = useCallback(() => {
    clearHideTimer();
    clearSavingTimer();
    savingTimerRef.current = setTimeout(() => {
      savingTimerRef.current = null;
      setSaveStatus("saving");
    }, SAVING_DISPLAY_DELAY_MS);
  }, [clearHideTimer, clearSavingTimer]);

  const reportSaved = useCallback(() => {
    clearHideTimer();
    clearSavingTimer();
    setSaveStatus("saved");
    hideTimerRef.current = setTimeout(() => setSaveStatus("idle"), SAVED_DISPLAY_MS);
  }, [clearHideTimer, clearSavingTimer]);

  const reportError = useCallback(() => {
    clearHideTimer();
    clearSavingTimer();
    setSaveStatus("error");
  }, [clearHideTimer, clearSavingTimer]);

  const resetSaveStatus = useCallback(() => {
    clearHideTimer();
    clearSavingTimer();
    setSaveStatus("idle");
  }, [clearHideTimer, clearSavingTimer]);

  useEffect(() => {
    return () => {
      clearHideTimer();
      clearSavingTimer();
    };
  }, [clearHideTimer, clearSavingTimer]);

  return { saveStatus, reportSaving, reportSaved, reportError, resetSaveStatus };
}
