import React, { useState, useEffect, useRef } from 'react';
import styles from './NavDrawer.module.scss';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function NavDrawer({ drawerOpen, onClose }) {
  const drawerRef = useRef(null);
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (drawerOpen) {
      // Focus drawer when opened
      drawerRef.current?.focus();

      // Handle Escape key
      const handleEscape = (e) => {
        if (e.key === 'Escape') {
          onClose();
        }
      };

      document.addEventListener('keydown', handleEscape);

      return () => {
        document.removeEventListener('keydown', handleEscape);
      };
    }
  }, [drawerOpen, onClose]);

  return (
    <>
      {/* Overlay */}
      <div
        className={`${styles.overlay} ${drawerOpen ? styles.visible : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <nav
        ref={drawerRef}
        className={`${styles["nav-drawer"]} ${drawerOpen ? styles.drawerOpen : ''}`}
        aria-label="Side navigation"
        aria-hidden={!drawerOpen}
        tabIndex={-1}
      >
        <div className={styles["nav-drawer-header"]}>
          <button onClick={onClose} aria-label="Close navigation drawer" className={styles.closeButton}>
            ✕
          </button>
        </div>

        <ul className={styles["nav-drawer-links"]} role="list">
          {isAuthenticated ? (
            <>
              <li><Link to="/activities" onClick={onClose} tabIndex={drawerOpen ? 0 : -1}>Activities</Link></li>
              {/* <li><Link to="/village" onClick={onClose} tabIndex={drawerOpen ? 0 : -1}>Village</Link></li> */}
            </>
          ) : (
            <>
              <li><Link to="/" onClick={onClose} tabIndex={drawerOpen ? 0 : -1}>Home</Link></li>
              <li><Link to="/login" onClick={onClose} tabIndex={drawerOpen ? 0 : -1}>Log in</Link></li>
              <li><Link to="/register" onClick={onClose} tabIndex={drawerOpen ? 0 : -1}>Join the waiting list</Link></li>
            </>
          )}
        </ul>
      </nav>
    </>
  );
}
