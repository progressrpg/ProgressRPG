import React from 'react';
import styles from './Profile.module.scss';
import Infobar from '../../layout/Infobar/Infobar';
import ProfileContent from '../../layout/Profile/ProfileContent.jsx';

export default function ProfilePage({
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
