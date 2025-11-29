import React, { useState } from 'react';
import styles from './NavDrawer.module.scss';
import { Link } from 'react-router-dom';

export default function NavDrawer() {
  const [open, setOpen] = useState(false);

  const toggleDrawer = () => setOpen(o => !o);
  const closeDrawer = () => setOpen(false);

  return (
    <>
      {/* Button to open drawer */}
      <button className={styles["open-drawer-btn"]} onClick={toggleDrawer}>
        ☰
      </button>

      {/* Overlay */}
      <div
        className={`${styles.overlay} ${open ? styles.visible : ''}`}
        onClick={closeDrawer}
      />

      {/* Drawer */}
      <nav className={`${styles["nav-drawer"]} ${open ? styles.open : ''}`}>
        <div className={styles["nav-drawer-header"]}>
          <button onClick={closeDrawer}>✕</button>
        </div>

        <ul className={styles["nav-drawer-links"]}>
          <li><Link to="/quests">Quests</Link></li>
          <li><Link to="/timers">Timers</Link></li>
          <li><Link to="/rewards">Rewards</Link></li>
          <li><Link to="/settings">Settings</Link></li>
          <li><Link to="/experimental">Experimental</Link></li>
        </ul>
      </nav>
    </>
  );
}
