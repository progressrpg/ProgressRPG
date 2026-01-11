// src/components/ActivityInput/ActivityInput.jsx
import { useState, useEffect, useRef } from "react";
import { useGame } from "../../context/GameContext";
import Input from "../Input/Input";
import Button from "../Button/Button";
import styles from "./ActivityInput.module.scss";

export default function ActivityInput() {
  const { activityTimer2, fetchCharacterCurrent, fetchActivities } = useGame();
  const {
    status,
    stop,
    startActivity,
    currentActivity,
    elapsed,
  } = activityTimer2;
  const [name, setName] = useState("");


  //console.log("timer:", activityTimer2);

  async function handleStart() {
    await startActivity(name);
    setName("");
  }

  async function handleStop() {
    await stop();
  }

  async function handleToggle() {
    if (isActive) {
      await stop(name);
      await Promise.all([fetchCharacterCurrent(), fetchActivities()]);
      return;
    }
    if (!name.trim()) return;
    await startActivity(name.trim());
  }

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  const isActive = status === "active";

  return (
    <div className={styles.container}>
      <div className={styles.row}>
        <div className={styles.grow}>
          <Input
              id="activity-name"
              // label="What are you working on?"
              value={name}
              onChange={setName}
              placeholder="What are you working on? e.g. washing dishes"
          />
        </div>

        <div className={styles.timerPill}>
          {minutes}:{seconds.toString().padStart(2, "0")}
        </div>

        <Button
          onClick={handleToggle}
          variant="primary"
          // disabled={!isActive && !name.trim()}
        >
            {isActive ? "Stop" : "Start"}
        </Button>
      </div>

        {/* Optional tiny status line */}
        <div className={styles.subRow}>
          <span className={styles.status}>
            {isActive ? "Running" : "Not running"}
          </span>
          {currentActivity && !isActive && (
            <span className={styles.hint}>Edit the name, then press Start to begin.</span>
          )}
        </div>


    </div>
  );
}
