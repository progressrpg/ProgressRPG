import React, { useMemo } from 'react';
import { useGame } from '../../context/GameContext';
import styles from './QuestTimer.module.scss';
import { formatDuration } from '../../../utils/formatUtils.js';
import TimerDisplay from './TimerDisplay.jsx';
import List from '../List/List.jsx';


export default function QuestTimer() {
  const { questTimer } = useGame();
  const {
    subject: quest,
    status,
    remaining,
    processedStages,
    globalStageIndex
  } = questTimer;
  const {
    name = 'None',
    intro_text = 'No active quest yet...',
    outro_text = ''
  } = quest || {};
  const displayTime = formatDuration(remaining);

  // console.log(`[Quest Timer] questTimer:`, questTimer);
  // console.log(`[Quest Timer] processedStages:`, processedStages);

  const visibleStages = useMemo(() => {
  return processedStages.map((item, index) => ({
      ...item,
      isHidden: index !== globalStageIndex,
    }));
  }, [processedStages, globalStageIndex]);

  return (
    <div className={styles.questRow}>
      <TimerDisplay
        label="Quest"
        status={status}
        time={displayTime}
      />

      <div className={styles.currentQuestSection}>
        <p className={styles.questText}>
          <span className={styles.questLabel}>Current quest:{' '}</span>
          <span className={styles.currentQuestTitle}>{name}</span>
        </p>
        <p className={styles.questText}>{intro_text}</p>

        <List
          items={visibleStages}
          renderItem={({ stage }) => stage?.text}
          getItemClassName={({ globalIndex }) => {
            if (globalIndex < globalStageIndex) return styles.completedStage;
            if (globalIndex === globalStageIndex) return styles.currentStage;
          return styles.futureStage;
          }}
          className={styles.list}
          sectionClass={styles.listSection}
        />

        <p
          className={styles.questText}
          style={{ display: status=="completed" ? 'flex' : 'none' }}
        >{outro_text}</p>
      </div>

    </div>
  );
}
