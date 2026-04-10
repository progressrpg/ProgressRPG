import { useEffect, useRef, useState } from "react";
import classNames from "classnames";
import { useGame } from "../../context/GameContext";
import Button from "../Button/Button";
import styles from "./ActivityInput.module.scss";
import { useSupportFlow } from "../../hooks/useSupportFlow";
import SupportFlowModal from "../SupportFlow/SupportFlowModal";

// Track whether the daily reward modal has been shown this browser session
const DAILY_REWARD_SESSION_KEY = "supportFlow_dailyRewardShown";

export default function ActivityInput() {
  const { activityTimer, fetchCharacterCurrent, fetchActivities } = useGame();
  const { currentActivity, status, stop, startActivity, elapsed } = activityTimer;

  const [name, setName] = useState("");
  const timeoutRef = useRef(null);
  const inputRef = useRef(null);

  const isActive = status === "active";

  const { openDailyReward, openActivityReward, flowState, flowDispatch, handleConfirmActivity } =
    useSupportFlow({
      onStartActivity: ({ activityText, durationSeconds }) => {
        startActivity({ text: activityText, limitSeconds: durationSeconds ?? null });
      },
    });

  // Show daily reward modal once per browser session
  useEffect(() => {
    if (!sessionStorage.getItem(DAILY_REWARD_SESSION_KEY)) {
      sessionStorage.setItem(DAILY_REWARD_SESSION_KEY, "true");
      openDailyReward();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  async function handleToggle() {
    if (isActive) {
      await stop(name);
      setName("");
      await Promise.all([fetchCharacterCurrent(), fetchActivities()]);
      openActivityReward();
      return;
    }

    if (!name.trim()) return;
    await startActivity(name.trim());
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

      </div>

      <SupportFlowModal
        state={flowState}
        dispatch={flowDispatch}
        onConfirmActivity={handleConfirmActivity}
      />
    </>
  );
}
