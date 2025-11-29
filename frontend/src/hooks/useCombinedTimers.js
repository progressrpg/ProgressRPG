// hooks/useCombinedTimers.js
import { useRef, useEffect } from 'react';
import { useGame } from '../context/GameContext';

export default function useCombinedTimers() {
  const { setPlayer, activityTimer, questTimer, fetchActivities, fetchQuests, showToast } = useGame();
  const timersRunningRef = useRef(false);
  const completingRef = useRef(false);

  // Auto-start both if both are ready
  useEffect(() => {
    const isReady = (status) => ["waiting", "paused"].includes(status);
    const bothReady = isReady(activityTimer.status) && isReady(questTimer.status);

    if (bothReady && !timersRunningRef.current) {
      // console.log('[COMBINED TIMERS] Both ready!');
      timersRunningRef.current = true;

      (async () => {
        if (isReady(activityTimer.status)) {
          await activityTimer.start();
        }
        if (isReady(questTimer.status)) {
          await questTimer.start();
        }
      })();
    }
  }, [
    activityTimer.status,
    questTimer.status,
  ]);

  // Submit activity
  const submitActivity = async () => {
    // console.log('[COMBINED TIMERS] Submit activity');

    timersRunningRef.current = false;
    const canComplete = (status) => ["active", "waiting", "paused"].includes(status);

    if (canComplete(activityTimer.status)) {
      const data = await activityTimer.complete();
      console.log("activity timer complete data:", data);
      if (data.profile) setPlayer(data.profile);
      await activityTimer.reset();
      await fetchActivities();

      if (questTimer.status !== "completed") questTimer.pause();
    }
  };

  // Quest auto-complete
  useEffect(() => {
    /* console.log('[COMBINED TIMERS] Checking quest completion', {
      status: questTimer.status,
      remaining: questTimer.remaining,
      completing: completingRef.current,

    }); */

    if (
      questTimer.status === "active" &&
      questTimer.remaining === 0 &&
      !completingRef.current
    ) {
      completingRef.current = true;
      questTimer.complete()
        .then(() => fetchQuests())
        .then(() => activityTimer.pause())
        .then(() => timersRunningRef.current = false)
        .catch((err) => {
          console.error('[COMBINED TIMERS] Quest completion error:', err);
          showToast("Something went wrong:", err);
        })
        .finally(() => {
          completingRef.current = false;
        });
    }
  }, [questTimer.remaining, questTimer.status]);

  return {
    submitActivity,
  };
}
