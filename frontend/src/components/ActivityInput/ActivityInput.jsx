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
    fetchPlayerAndCharacter,
    fetchCharacterCurrent,
    fetchActivities,
    loginState,
    loginStreak,
    loginEventAt,
    player,
    freeTimerLimitSeconds,
  } = useGame();
  const {
    currentActivity,
    status,
    stop,
    startActivity,
    elapsed,
    limitSeconds,
    limitReached,
    autoStopCompletion,
    clearAutoStopCompletion,
  } = activityTimer;

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

  useEffect(() => {
    if (!autoStopCompletion) return;

    let cancelled = false;

    async function handleAutoStopCompletion() {
      setName("");

      try {
        await Promise.all([
          fetchPlayerAndCharacter(),
          fetchCharacterCurrent(),
          fetchActivities(),
        ]);
      } catch (err) {
        console.error("[ActivityInput] Failed to refresh after auto-stop:", err);
      }

      if (cancelled) return;

      openActivityReward({
        xpGained: autoStopCompletion.xpGained,
        baseXp: autoStopCompletion.baseXp,
        xpMultiplier: autoStopCompletion.xpMultiplier,
        levelUps: autoStopCompletion.levelUps,
        activityName: autoStopCompletion.activityName,
        elapsedSeconds: autoStopCompletion.elapsedSeconds,
      });
      clearAutoStopCompletion();
    }

    handleAutoStopCompletion();

    return () => {
      cancelled = true;
    };
  }, [
    autoStopCompletion,
    clearAutoStopCompletion,
    fetchPlayerAndCharacter,
    fetchActivities,
    fetchCharacterCurrent,
    openActivityReward,
  ]);

  async function handleToggle() {
    if (isActive) {
      const completedActivityName = (name || currentActivity?.name || "").trim();
      const completion = await stop({ activityName: name });
      const xpGained = completion?.xp_gained ?? null;
      const baseXp = completion?.base_xp ?? null;
      const xpMultiplier = completion?.xp_multiplier ?? null;
      const levelUps = completion?.level_ups ?? [];
      const elapsedSeconds = completion?.duration_seconds ?? elapsed;
      setName("");
      await Promise.all([
        fetchPlayerAndCharacter(),
        fetchCharacterCurrent(),
        fetchActivities(),
      ]);
      openActivityReward({
        xpGained,
        baseXp,
        xpMultiplier,
        levelUps,
        activityName: completedActivityName || null,
        elapsedSeconds,
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
  const formattedLimit =
    typeof limitSeconds === "number" && limitSeconds > 0
      ? `${Math.floor(limitSeconds / 60)}:${(limitSeconds % 60)
          .toString()
          .padStart(2, "0")}`
      : null;
  const warningThresholdSeconds =
    typeof limitSeconds === "number" && limitSeconds > 0
      ? limitSeconds * 0.9
      : null;
  const showAutoStopWarning =
    isActive &&
    typeof limitSeconds === "number" &&
    limitSeconds > 0 &&
    warningThresholdSeconds !== null &&
    elapsed >= warningThresholdSeconds &&
    elapsed < limitSeconds;

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

        {showAutoStopWarning && (
          <p className={styles.limitWarning}>
            This timer will stop automatically when it reaches {formattedLimit}.
          </p>
        )}

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
