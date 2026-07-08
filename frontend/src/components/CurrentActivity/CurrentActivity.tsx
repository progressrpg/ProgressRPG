import React from "react";
import classNames from "classnames";
import { useGame } from "../../hooks/useGame";
import ActivityInput from "../ActivityInput/ActivityInput";
import styles from "./CurrentActivity.module.scss";

export default function CurrentActivity() {
  const { activityTimer } = useGame();
  const isActive = activityTimer?.status === "active";
  const elapsed = activityTimer?.elapsed ?? 0;
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  return (
    <section className={classNames(styles.wrapper, { [styles.isActive]: isActive })}>
      <div className={classNames(styles.headingRow, { [styles.isRunning]: isActive })}>
        <h2 className={styles.heading}>Timer</h2>
        <div className={styles.timerPill}>
          {minutes}:{seconds.toString().padStart(2, "0")}
        </div>
      </div>
      <div className={styles.playerCard}>
        <ActivityInput />
      </div>
    </section>
  );
}
