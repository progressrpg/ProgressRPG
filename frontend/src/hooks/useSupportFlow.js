// hooks/useSupportFlow.js
// Hook that manages SupportFlow modal state and exposes a clean API to callers.
//
// Usage:
//   const { openWelcomeMessage, openActivityReward, flowState, flowDispatch, handleConfirmActivity }
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

  const openWelcomeMessage = useCallback(({ loginState = "none", loginStreak = 0, loginRewardXp = 0 } = {}) => {
    flowDispatch({ type: "OPEN_WELCOME_MESSAGE", loginState, loginStreak, loginRewardXp });
  }, []);

  const openActivityReward = useCallback(
    ({
      xpGained = null,
      activityName = null,
      elapsedSeconds = null,
      baseXp = null,
      xpMultiplier = null,
      levelUps = [],
      isAutoStopped = false,
      showUpgradePrompt = false,
    } = {}) => {
      flowDispatch({
        type: "OPEN_ACTIVITY_REWARD",
        xpGained,
        activityName,
        elapsedSeconds,
        baseXp,
        xpMultiplier,
        levelUps,
        isAutoStopped,
        showUpgradePrompt,
      });
    },
    []
  );

  const openSupportMode = useCallback(() => {
    flowDispatch({ type: "OPEN_SUPPORT_MODE" });
  }, []);

  const handleConfirmActivity = useCallback((activityTextOverride = null) => {
    const state = flowStateRef.current;
    if (!state.isOpen) return;
    const { activityText, durationSeconds } = state.ctx;
    const finalActivityText =
      typeof activityTextOverride === "string"
        ? activityTextOverride
        : activityText;
    onStartActivity?.({ activityText: finalActivityText, durationSeconds });
    flowDispatch({ type: "CLOSE" });
  }, [onStartActivity]);

  return {
    openWelcomeMessage,
    openActivityReward,
    openSupportMode,
    flowState,
    flowDispatch,
    handleConfirmActivity,
  };
}
