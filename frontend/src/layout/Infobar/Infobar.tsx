import React from "react";
import { useGame } from "../../hooks/useGame";
import AchievementBadges from "./AchievementBadges";
import styles from "./Infobar.module.scss";

export default function Infobar() {
  const { player, loading } = useGame();

  if (loading) {
    return (
      <div
        className={styles.infoBar}
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <span className="sr-only">Loading data...</span>
      </div>
    );
  }

  if (!player || !player.progressive_unlocks.infobar) {
    return null;
  }

  const currentXp = player.xp ?? 0;
  const nextLevelXp = player.xp_next_level ?? 0;

  return (
    <div className={styles.infoBar}>
      <div className={`${styles.infoBox} ${styles.player}`}>
        <div
          className={`${styles.accountIcon}${player.is_premium ? ` ${styles.accountIconPremium}` : ""}`}
          aria-hidden="true"
        >
          <svg viewBox="0 0 24 24" focusable="false">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" />
          </svg>
        </div>
        <span className={styles.value}>{player.name}</span>
        <div className={styles.achievementsColumn}>
          <AchievementBadges achievements={player.achievements} />
        </div>
        <div className={styles.statsColumn}>
          <span className={styles.level}>Level {player.level}</span>
          <span className={styles.xp}>
            XP: {currentXp} / {nextLevelXp}
          </span>
        </div>
      </div>
    </div>
  );
}
