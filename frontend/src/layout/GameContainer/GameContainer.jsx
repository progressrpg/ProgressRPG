import React, { useState } from 'react';
import GameContent from './GameContent';
import styles from './GameContainer.module.scss';
import Infobar from '../Infobar/Infobar';

export default function GameContainer({
}) {

  return (
    <div className={styles.gameContainer}>
      <Infobar />
      <GameContent />
    </div>
  );
}
