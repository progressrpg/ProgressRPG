import React, { useState } from 'react';
import styles from './NavDrawer.module.scss';
import { Link } from 'react-router-dom';

export default function NavDrawer({ drawerOpen, onClose }) {

  return (
    <>
      {/* Overlay */}
      <div
        className={`${styles.overlay} ${drawerOpen ? styles.visible : ''}`}
        onClick={onClose}
      />

      {/* Drawer */}
      <nav className={`${styles["nav-drawer"]} ${drawerOpen ? styles.drawerOpen : ''}`}>
        <div className={styles["nav-drawer-header"]}>
          <button onClick={onClose} className={styles.closeButton} aria-label="Close menu">
            ✕
          </button>
        </div>

        <ul className={styles["nav-drawer-links"]}>
          <li><Link to="/account" onClick={onClose}>Your account</Link></li>
          <li><Link to="/activities" onClick={onClose}>Your activities</Link></li>
          <li><Link to="/game" onClick={onClose}>Game</Link></li>
        </ul>
      </nav>
    </>
  );
}
