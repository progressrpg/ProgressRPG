import React, { useState } from 'react';
import GameContent from './GameContent';
import styles from './GameContainer.module.scss';
import Infobar from '../Infobar/Infobar';

export default function GameContainer({ onboardingStage }) {

  return (
    <div className={styles.gameContainer}>
      {onboardingStage >= 4 && (
        <Infobar />
      )}
      <GameContent onboardingStage={onboardingStage} />
    </div>
  );
}
