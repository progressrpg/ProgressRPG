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
  const { activityTimer, questTimer, showToast } = useGame();

  const timersRunningRef = useRef(false);
  const completingRef = useRef(false);

  // Auto-start logic
  useEffect(() => {
    if (!autoStart) return;

    const isReady = (status) => ["waiting", "paused"].includes(status);

    const activityReady = isReady(activityTimer.status);
    const questReady = enablequest && questTimer ? isReady(questTimer.status) : false;

    if (activityReady && !timersRunningRef.current) {
      timersRunningRef.current = true;

      (async () => {
        try {
          await activityTimer.start();
          if (questReady) {
            await questTimer.start();
          }
        } catch (err) {
          onError?.(err);
        }
      })();
  }, [
    autoStart,
    enableQuest,
    activityTimer.status,
    questTimer?.status,
  ]);

  // Submit activity
  const submitActivity = async () => {
    timersRunningRef.current = false;

    const canComplete = (status) => ["active", "waiting", "paused"].includes(status);

    if (canComplete(activityTimer.status)) {
      try {
        const data = await activityTimer.complete();

        onActivityComplete?.(data);

      await activityTimer.reset();

      if (enableQuest && questTimer && questTimer.status !== "completed") {
        questTimer.pause();
      }
    }
  };

  // Quest auto-complete
  useEffect(() => {
    if (!enableQuest) return;
    if (!questTimer) return;

    const shouldComplete =
        questTimer.status === "active" &&
        questTimer.remaining === 0 &&
        !completingRef.current;

    if (shouldComplete) {
      completingRef.current = true;
      questTimer
        .complete()
        .then((data) => {
          onQuestComplete?.(data);

          if (enableQuest) {
            activityTimer.pause();
          }

          timersRunningRef.current = false;
        })
        .catch((err) => {
          onError?.(err);
        })
        .finally(() => {
          completingRef.current = false;
        });
    }
  }, [
    enableQuest,
    questTimer?.remaining,
    questTimer?.status,
]);

  return {
    submitActivity,
    mode: enableQuest ? "combined" : "activity-only",
  };
}
