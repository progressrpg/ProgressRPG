import React, { useState } from 'react';
import GameContent from './GameContent';
import styles from './GameContainer.module.scss';
import Infobar from '../Infobar/Infobar';
import { useGame } from '../../context/GameContext';

export default function GameContainer() {
  const {onboardingStage} = useGame();

  return (
    <div className={styles.gameContainer}>
      {onboardingStage >= 4 && (
        <Infobar />
      )}
      <GameContent onboardingStage={onboardingStage} />
    </div>
  );
}
