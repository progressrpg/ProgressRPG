import React from 'react';
import List from '../../../components/List/List';
import styles from './ActivityPanel.module.scss';
import { useGame } from '../../../context/GameContext';
import { formatDuration } from '../../../../utils/formatUtils';

export default function ActivityPanel() {
  const { activities } = useGame();
  const totalDuration = activities?.results?.reduce((acc, a) => acc + a.duration, 0) || 0;
  const count = activities?.count || 0;
  //console.log("activities:", activities);
  return (
    <section className={styles.listSection}>
      <h2>Today's activities</h2>

      <div className={styles.row}>
        <div className={styles.activityTotals}>
          <span>{formatDuration(totalDuration)}</span>
          <span>time and</span>
          <span>{count}</span>
          <span>activities logged today</span>
        </div>
      </div>

      {count === 0 ? (
        <p>No activities completed today...so far!</p>
      ) : (
        <List
          items={activities}
          renderItem={(act) => (
            <div>
              {act.name} – {formatDuration(act.duration)}
            </div>
          )}
          className={styles.list}
        />
      )}
    </section>
  );
}
