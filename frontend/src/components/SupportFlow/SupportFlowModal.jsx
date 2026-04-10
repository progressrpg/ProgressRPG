// SupportFlow/SupportFlowModal.jsx
// Container component that routes to the correct screen based on flow state.
// Does NOT own state – the parent controls state via useSupportFlow().

import { useCallback } from "react";
import Modal from "../Modal/Modal";
import WelcomeMessageScreen from "./screens/WelcomeMessageScreen";
import ActivityRewardScreen from "./screens/ActivityRewardScreen";
import SupportMenuScreen from "./screens/SupportMenuScreen";
import ActivityMenuScreen from "./screens/ActivityMenuScreen";
import ActivityInputScreen from "./screens/ActivityInputScreen";
import NotReadyMenuScreen from "./screens/NotReadyMenuScreen";
import SupportDetailScreen from "./screens/SupportDetailScreen";
import PostSupportMenuScreen from "./screens/PostSupportMenuScreen";

// Screen title lookup – keeps JSX clean
const SCREEN_TITLES = {
  WELCOME_MESSAGE: "Welcome!",
  ACTIVITY_REWARD: "Activity complete!",
  SUPPORT_MENU: "How are you feeling?",
  READY_ACTIVITY_MENU: "Choose an activity",
  ACTIVITY_INPUT: "Describe your activity",
  NOT_READY_MENU: "Let's support you",
  SUPPORT_DETAIL: "Support steps",
  POST_SUPPORT_MENU: "How are you feeling now?",
};

export default function SupportFlowModal({ state, dispatch, onConfirmActivity }) {
  // Stable close reference – prevents Modal's useEffect([onClose]) from
  // re-running (and stealing focus) on every keystroke in text inputs.
  const close = useCallback(() => {
    dispatch({ type: "CLOSE" });
  }, [dispatch]);

  if (!state.isOpen) return null;

  const { screen, ctx } = state;
  const canBackToReward =
    screen === "SUPPORT_MENU" &&
    ctx.supportMenuOrigin === "reward";

  let onHeaderBack = null;
  if (canBackToReward) {
    onHeaderBack = () => dispatch({ type: "BACK_FROM_SUPPORT_MENU" });
  } else if (screen === "READY_ACTIVITY_MENU" || screen === "NOT_READY_MENU") {
    onHeaderBack = () => dispatch({ type: "GO_SUPPORT_MENU" });
  } else if (screen === "ACTIVITY_INPUT") {
    onHeaderBack = () => dispatch({ type: "READY_START" });
  }

  function renderScreen() {
    switch (screen) {
      case "WELCOME_MESSAGE":
        return (
          <WelcomeMessageScreen
            loginState={ctx.welcomeMessageLoginState}
            loginStreak={ctx.welcomeMessageLoginStreak}
            onStart={close}
            onSupport={() => dispatch({ type: "GO_SUPPORT_MENU", origin: "reward" })}
          />
        );

      case "ACTIVITY_REWARD":
        return (
          <ActivityRewardScreen
            xpGained={ctx.xpGained}
            activityName={ctx.completedActivityName}
            onContinue={close}
            onSupport={() => dispatch({ type: "GO_SUPPORT_MENU", origin: "reward" })}
          />
        );

      case "SUPPORT_MENU":
        return (
          <SupportMenuScreen
            onReady={() => dispatch({ type: "READY_START" })}
            onNotReady={() => dispatch({ type: "NOT_READY" })}
          />
        );

      case "READY_ACTIVITY_MENU":
        return (
          <ActivityMenuScreen
            onPickPreset={(preset) =>
              dispatch({ type: "PICK_ACTIVITY_PRESET", preset })
            }
          />
        );

      case "ACTIVITY_INPUT":
        return (
          <ActivityInputScreen
            activityPresetId={ctx.activityPresetId}
            activityText={ctx.activityText}
            durationSeconds={ctx.durationSeconds}
            onChangeText={(text) =>
              dispatch({ type: "SET_ACTIVITY_TEXT", text })
            }
            onChangeDuration={(seconds) =>
              dispatch({ type: "SET_DURATION_SECONDS", seconds })
            }
            onConfirm={onConfirmActivity}
            onConfirmWithText={(text) => onConfirmActivity(text)}
          />
        );

      case "NOT_READY_MENU":
        return (
          <NotReadyMenuScreen
            onPick={(id) => dispatch({ type: "PICK_SUPPORT_ACTION", id })}
          />
        );

      case "SUPPORT_DETAIL":
        return (
          <SupportDetailScreen
            supportActionId={ctx.supportActionId}
            onBackToSupportMenu={() =>
              dispatch({ type: "GO_SUPPORT_MENU", origin: "regulation" })
            }
          />
        );

      case "POST_SUPPORT_MENU":
        return (
          <PostSupportMenuScreen
            onTryTask={() => dispatch({ type: "POST_SUPPORT_TRY_TASK" })}
            onMoreSupport={() =>
              dispatch({ type: "POST_SUPPORT_MORE_SUPPORT" })
            }
          />
        );

      default:
        return null;
    }
  }

  return (
    <Modal
      id="support-flow-modal"
      title={SCREEN_TITLES[screen] ?? "Support"}
      onClose={close}
      onBack={onHeaderBack}
    >
      {renderScreen()}
    </Modal>
  );
}
