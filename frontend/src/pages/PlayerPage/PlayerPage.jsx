import React from 'react';
import styles from './Profile.module.scss';
import Infobar from '../../layout/Infobar/Infobar.jsx';
import ProfileContent from '../../layout/Player/PlayerContent.jsx';

export default function PlayerPage({
}) {

  return (
    <div className={styles.page}>
      <Infobar />
      <div className={styles.content}>
        <ProfileContent />
      </div>
    </div>
  );
}
