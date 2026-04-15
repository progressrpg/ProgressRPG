import React from 'react';
import { useGame } from '../../context/GameContext';
import styles from './Infobar.module.scss';

export default function Infobar() {
  const { player, loading } = useGame();

  // const { player, character, xpMods, loading } = useGame();


  if (loading) {
    return (
      <div className={styles.infoBar} role="status" aria-live="polite" aria-busy="true">
        <span className="sr-only">Loading data...</span>
      </div>
    );
  }

  if (!player) {
    return null;
  }

  // if (!player || !character) {
  //   return null;
  // }

  // Format XP modifier display
  // const formatXpMods = () => {
  //   if (!xpMods || xpMods.length === 0) {
  //     return 'No active modifiers';
  //   }

  //   return xpMods.map((mod) => {
  //     const keyDisplay = mod.key.replace('_', ' ').toUpperCase();
  //     return `${keyDisplay} (${mod.multiplier}x)`;
  //   }).join(', ');
  // };

  const currentXp = player?.xp ?? 0;
  const nextLevelXp = player?.xp_next_level ?? 0;

  return (
    <div className={styles.infoBar}>
      <div className={`${styles.infoBox} ${styles.player}`}>
        <div className={styles.accountIcon} aria-hidden="true">
          <svg viewBox="0 0 24 24" focusable="false">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" />
          </svg>
        </div>
        <div className={styles.details}>
          <div className={styles.content}>
            <span className={styles.value}>{player.name}</span>
            <span className={styles.level}>Level {player.level}</span>
          </div>
          <div className={styles.content}>
            <span className={styles.xp}>XP: {currentXp} / {nextLevelXp}</span>
          </div>
        </div>
      </div>

      {/*
      <div className={`${styles.infoBox} ${styles.modifiers}`}>
        <span className={styles.xpModifiers}>{formatXpMods()}</span>
      </div>

      {character && (
        <div className={`${styles.infoBox} ${styles.character}`}>
          <span className={styles.label}>CHARACTER</span>
          <div className={styles.content}>
            <span className={styles.value}>{character.first_name}</span>
            <span className={styles.level}>Lv. {character.level}</span>
          </div>
        </div>
      )}
      */}
    </div>
  );
}
