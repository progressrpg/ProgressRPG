// hooks/useCombinedTimers.js
import { useRef, useEffect } from 'react';
import { useGame } from '../context/GameContext';

export default function useCombinedTimers({
  enableQuest = true,     // onboarding: false, gameplay: true
  autoStart = true,       // onboarding: false, gameplay: true
  onActivityComplete,     // callback for UI updates
  onQuestComplete,        // callback for UI updates
  onError,                // callback for toast or logging
}) {
  const { activityTimer, questTimer } = useGame();

  const timersRunningRef = useRef(false);
  const completingRef = useRef(false);

  // Safe error handler
  const handleError = (err) => {
    console.error(err);
    if (typeof onError === 'function') {
      onError(err);
    }
  };

  // Auto-start logic
  useEffect(() => {
    if (!autoStart) return;

    const isReady = (status) => ["waiting", "paused"].includes(status);

    const startTimers = async () => {
      if ((activityTimer && isReady(activityTimer.status)) ||
        (enableQuest && questTimer && isReady(questTimer.status))) {
        try {
          if (activityTimer && isReady(activityTimer.status)) {
            await activityTimer.start();
          }
          if (enableQuest && questTimer && isReady(questTimer.status)) {
            await questTimer.start();
          }
          timersRunningRef.current = true;
        } catch (err) {
          handleError(err);
          timersRunningRef.current = false;
        }
      }
    };

    startTimers();

  }, [
    autoStart,
    enableQuest,
    activityTimer,
    questTimer,
    onError,
  ]);

  // Submit activity
  const submitActivity = async ( extraData = {} ) => {
    timersRunningRef.current = false;

    const canComplete = (status) =>
      ["active", "waiting", "paused"].includes(status);

    if (!activityTimer || !canComplete(activityTimer.status)) return;

    try {
      const data = await activityTimer.complete();
      onActivityComplete?.(data);

      await activityTimer.reset();

      if (enableQuest && questTimer && questTimer.status !== "completed") {
        questTimer.pause();
      }
      return data;
    } catch (err) {
      handleError(err);
      console.error("Failed to complete activity:", err);
    }
  };

  // Quest auto-complete
  useEffect(() => {
    if (!enableQuest || !questTimer) return;

    const checkQuestCompletion = async () => {
      if (
        questTimer.status === "active" &&
        questTimer.remaining === 0 &&
        !completingRef.current
      ) {
        completingRef.current = true;
        try {
          const data = await questTimer.complete();
          onQuestComplete?.(data);
          activityTimer?.pause();
          timersRunningRef.current = false;
        } catch (err) {
          handleError(err);
          console.error("Failed to auto-complete quest:", err);
        } finally {
          completingRef.current = false;
        }
      }
    };

    const interval = setInterval(checkQuestCompletion, 500);
    return () => clearInterval(interval);
  }, [
    enableQuest,
    activityTimer,
    questTimer,
    onQuestComplete,
    onError,
]);

  return {
    submitActivity,
    mode: enableQuest ? "combined" : "activity-only",
  };
}
