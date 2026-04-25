import { useEffect, useRef, useState } from "react";
import classNames from "classnames";
import { useGame } from "../../context/GameContext";
import Button from "../Button/Button";
import styles from "./ActivityInput.module.scss";
import { useSupportFlow } from "../../hooks/useSupportFlow";
import SupportFlowModal from "../SupportFlow/SupportFlowModal";
import { playLimitReachedSound } from "../../utils/sounds";

const WELCOME_MESSAGE_LAST_EVENT_KEY = "supportFlow_lastLoginEventAtShown";

export default function ActivityInput() {
  const {
    activityTimer,
    fetchCharacterCurrent,
    fetchActivities,
    loginState,
    loginStreak,
    loginEventAt,
    player,
    freeTimerLimitSeconds,
  } = useGame();
  const { currentActivity, status, stop, startActivity, elapsed, limitReached } = activityTimer;

  const isPremium = Boolean(player?.is_premium);

  const [name, setName] = useState("");
  const timeoutRef = useRef(null);
  const inputRef = useRef(null);

  const isActive = status === "active";

  const {
    openWelcomeMessage,
    openActivityReward,
    openSupportMode,
    flowState,
    flowDispatch,
    handleConfirmActivity,
  } =
    useSupportFlow({
      onStartActivity: ({ activityText, durationSeconds }) => {
        const limitSeconds = isPremium
          ? (durationSeconds ?? null)
          : durationSeconds ? Math.min(durationSeconds, freeTimerLimitSeconds) : freeTimerLimitSeconds;
        startActivity({ text: activityText, limitSeconds });
      },
    });

  useEffect(() => {
    if (loginState === "none" || !loginEventAt) return;

    let lastShownEventAt = null;
    try {
      lastShownEventAt = sessionStorage.getItem(WELCOME_MESSAGE_LAST_EVENT_KEY);
    } catch {
      // If sessionStorage is unavailable, fall back to opening the modal.
    }

    if (lastShownEventAt === loginEventAt) return;

    openWelcomeMessage({ loginState, loginStreak });

    try {
      sessionStorage.setItem(WELCOME_MESSAGE_LAST_EVENT_KEY, loginEventAt);
    } catch {
      // Ignore storage failures and keep app flow functional.
    }
  }, [loginState, loginStreak, loginEventAt, openWelcomeMessage]);

  useEffect(() => () => timeoutRef.current && clearTimeout(timeoutRef.current), []);

  useEffect(() => {
    if (!inputRef.current) return;
    inputRef.current.style.height = "auto";
    inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
  }, [name]);

  useEffect(() => {
    if (status === "active" && currentActivity?.name) {
      setName(currentActivity.name);
    }
  }, [status, currentActivity]);

  useEffect(() => {
    if (limitReached) playLimitReachedSound();
  }, [limitReached]);

  async function handleToggle() {
    if (isActive) {
      const completedActivityName = (name || currentActivity?.name || "").trim();
      const completion = await stop({ activityName: name });
      const xpGained = completion?.xp_gained ?? null;
      setName("");
      await Promise.all([fetchCharacterCurrent(), fetchActivities()]);
      openActivityReward({
        xpGained,
        activityName: completedActivityName || null,
      });
      return;
    }

    if (!name.trim()) return;
    await startActivity({ text: name.trim(), limitSeconds: isPremium ? null : freeTimerLimitSeconds });
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey && !isActive && name.trim()) {
      e.preventDefault();
      handleToggle();

      e.currentTarget.blur();
    }
  }

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  return (
    <>
      <div className={styles.containerOuter}>
        <div
          className={classNames(styles.container, {
            [styles.isRunning]: isActive,
            [styles.needsAttention]: !isActive,
          })}
        >
          <div className={styles.row}>
            <div className={styles.grow}>
              <textarea
                id="activity-name"
                ref={inputRef}
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="What are you working on? e.g. washing dishes"
                className={classNames(styles.inputText, {
                  [styles.inputCTA]: !isActive,
                  [styles.inputMuted]: isActive,
                })}
                rows={1}
                aria-label="Activity name"
              />
            </div>

            <div className={classNames(styles.timerPill, styles.control)}>
              {minutes}:{seconds.toString().padStart(2, "0")}
            </div>

            <Button
              onClick={handleToggle}
              variant="primary"
              disabled={!isActive && !name.trim()}
              className={classNames(styles.ctaButton, styles.control)}
            >
              {isActive ? "Stop" : "Start"}
            </Button>
          </div>

        </div>

        <div className={styles.supportButtonRow}>
          <Button
            onClick={openSupportMode}
            variant="secondary"
            className={styles.supportModeButton}
            ariaLabel="Open support mode"
          >
            Need support?
          </Button>
        </div>

      </div>

      <SupportFlowModal
        state={flowState}
        dispatch={flowDispatch}
        onConfirmActivity={handleConfirmActivity}
      />
    </>
  );
}
