import { useEffect, useRef, useState } from "react";
import classNames from "classnames";
import { useGame } from "../../context/GameContext";
import Input from "../Input/Input";
import Button from "../Button/Button";
import styles from "./ActivityInput.module.scss";

export default function ActivityInput() {
  const { activityTimer, fetchCharacterCurrent, fetchActivities } = useGame();
  const { status, stop, startActivity, elapsed } = activityTimer;

  const [name, setName] = useState("");
  const timeoutRef = useRef(null);

  const isActive = status === "active";


  useEffect(() => () => timeoutRef.current && clearTimeout(timeoutRef.current), []);

  async function handleToggle() {
    if (isActive) {
      await stop(name);
      setName("");
      await Promise.all([fetchCharacterCurrent(), fetchActivities()]);
      return;
    }

    if (!name.trim()) return;
    await startActivity(name.trim());
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !isActive && name.trim()) {
      e.preventDefault();
      handleToggle();
    }
  }

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  return (
    <div className={styles.containerOuter}>

      <div
        className={classNames(styles.container, {
          [styles.isRunning]: isActive,
          [styles.needsAttention]: !isActive,
        })}
      >
        <div className={styles.row}>
          <div className={styles.grow}>
            <Input
              id="activity-name"
              value={name}
              onChange={setName}
              onKeyDown={handleKeyDown}
              placeholder="What are you working on? e.g. washing dishes"
              inputClassName={classNames(styles.control, {
                [styles.inputCTA]: !isActive,
                [styles.inputMuted]: isActive,
              })}
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

        <div className={styles.subRow}>
          <span className={styles.status}>{isActive ? "Running" : "Not running"}</span>
        </div>
      </div>

    </div>
  );
}
