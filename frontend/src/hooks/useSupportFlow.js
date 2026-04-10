// hooks/useSupportFlow.js
// Hook that manages SupportFlow modal state and exposes a clean API to callers.
//
// Usage:
//   const { openDailyReward, openActivityReward, flowState, flowDispatch, handleConfirmActivity }
//     = useSupportFlow({ onStartActivity });
//
// Then render <SupportFlowModal state={flowState} dispatch={flowDispatch} onConfirmActivity={handleConfirmActivity} />

import { useReducer, useCallback, useRef, useEffect } from "react";
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

  // Keep a ref to the latest flowState so handleConfirmActivity doesn't
  // get recreated on every keystroke in the activity text input.
  const flowStateRef = useRef(flowState);
  useEffect(() => { flowStateRef.current = flowState; }, [flowState]);

  const openDailyReward = useCallback(() => {
    flowDispatch({ type: "OPEN_DAILY_REWARD" });
  }, []);

  const openActivityReward = useCallback(() => {
    flowDispatch({ type: "OPEN_ACTIVITY_REWARD" });
  }, []);

  const handleConfirmActivity = useCallback(() => {
    const state = flowStateRef.current;
    if (!state.isOpen) return;
    const { activityText, durationSeconds } = state.ctx;
    onStartActivity?.({ activityText, durationSeconds });
    flowDispatch({ type: "CLOSE" });
  }, [onStartActivity]);

  return {
    openDailyReward,
    openActivityReward,
    flowState,
    flowDispatch,
    handleConfirmActivity,
  };
}
