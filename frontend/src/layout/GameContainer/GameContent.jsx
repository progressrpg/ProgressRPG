// layout/GameContainer/GameContent.jsx

import React from 'react';
import ActivitySection from './ActivitySection/ActivitySection';
import QuestSection from './QuestSection/QuestSection';
import styles from './GameContent.module.scss';


export default function GameContent() {

  return (
    <div className={styles.gameContent}>
      <ActivitySection />
      <QuestSection />
    </div>
  );
}
