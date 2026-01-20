import React from 'react';
import { useGame } from '../../context/GameContext';
import Infobox from './Infobox/Infobox';
import styles from './Infobar.module.scss';

export default function Infobar() {
  const { player, character, loading } = useGame();


  if (loading) {
    return (
      <div className={styles.infoBar} role="status" aria-live="polite" aria-busy="true">
        <span className="sr-only">Loading data...</span>
      </div>
    );
  }
  
  if (!player || !character) {
    return (
      <div className={styles.infoBar} role="status" aria-live="polite" aria-busy="true">
        <span className="sr-only">Loading player/character info...</span>
      </div>
    );
  }

  return (
    <div className={styles.infoBar}>
      <Infobox title="Player Info" type="player" data={player} />
      <Infobox title="Character Info" type="character" data={character} />
    </div>
  );
}
