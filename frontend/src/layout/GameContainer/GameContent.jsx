// layout/GameContainer/GameContent.jsx

import React from 'react';
import ActivitySection from './ActivitySection/ActivitySection';
import QuestSection from './QuestSection/QuestSection';
import styles from './GameContent.module.scss';
import { useGame } from '../../context/GameContext.jsx'

export default function GameContent() {
  const { onboardingStage } = useGame();

  return (
    <div className={styles.gameContent}>
      <ActivitySection onboardingStage={onboardingStage} />
      {onboardingStage >= 3 && (
        <QuestSection />
      )}
    </div>
  );
}
