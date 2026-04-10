// hooks/useSupportFlow.js
// Hook that manages SupportFlow modal state and exposes a clean API to callers.
//
// Usage:
//   const { openDailyReward, openActivityReward, flowState, flowDispatch, handleConfirmActivity }
//     = useSupportFlow({ onStartActivity });
//
// Then render <SupportFlowModal state={flowState} dispatch={flowDispatch} onConfirmActivity={handleConfirmActivity} />

import { useReducer, useCallback } from "react";
import { supportFlowReducer } from "../components/SupportFlow/supportFlowReducer";

/**
 * @param {object} options
 * @param {(payload: { activityText: string, durationSeconds: number|null }) => void} options.onStartActivity
 *   Callback invoked when the user confirms an activity in the modal.
 *   The parent should wire this to startActivity({ text, limitSeconds }).
 */
export function useSupportFlow({ onStartActivity } = {}) {
  const [flowState, flowDispatch] = useReducer(supportFlowReducer, {
    isOpen: false,
  });

  const openDailyReward = useCallback(() => {
    flowDispatch({ type: "OPEN_DAILY_REWARD" });
  }, []);

  const openActivityReward = useCallback(() => {
    flowDispatch({ type: "OPEN_ACTIVITY_REWARD" });
  }, []);

  const handleConfirmActivity = useCallback(() => {
    if (!flowState.isOpen) return;
    const { activityText, durationSeconds } = flowState.ctx;
    onStartActivity?.({ activityText, durationSeconds });
    flowDispatch({ type: "CLOSE" });
  }, [flowState, onStartActivity]);

  return {
    openDailyReward,
    openActivityReward,
    flowState,
    flowDispatch,
    handleConfirmActivity,
  };
}
