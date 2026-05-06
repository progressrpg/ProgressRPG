import React, { useCallback, useEffect, useRef } from 'react';
import styles from './NavDrawer.module.scss';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function NavDrawer({ drawerOpen, onClose }) {
  const drawerRef = useRef(null);
  const { isAuthenticated } = useAuth();

  const handleClose = useCallback(() => {
    const activeElement = document.activeElement;
    if (drawerRef.current?.contains(activeElement)) {
      activeElement?.blur?.();
    }

    onClose();
  }, [onClose]);

  useEffect(() => {
    if (drawerOpen) {
      // Focus drawer when opened
      drawerRef.current?.focus();

      // Handle Escape key
      const handleEscape = (e) => {
        if (e.key === 'Escape') {
          handleClose();
        }
      };

      document.addEventListener('keydown', handleEscape);

      return () => {
        document.removeEventListener('keydown', handleEscape);
      };
    }
  }, [drawerOpen, handleClose]);

  return (
    <>
      {/* Overlay */}
      <div
        className={`${styles.overlay} ${drawerOpen ? styles.visible : ''}`}
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <nav
        ref={drawerRef}
        className={`${styles["nav-drawer"]} ${drawerOpen ? styles.drawerOpen : ''}`}
        aria-label="Side navigation"
        aria-hidden={!drawerOpen}
        inert={!drawerOpen}
        tabIndex={-1}
      >
        <div className={styles["nav-drawer-header"]}>
          <button onClick={handleClose} aria-label="Close navigation drawer" className={styles.closeButton}>
            ✕
          </button>
        </div>

        <ul className={styles["nav-drawer-links"]} role="list">
          {isAuthenticated ? (
            <>
              <li><Link to="/timer" onClick={handleClose} tabIndex={drawerOpen ? 0 : -1}>Timer</Link></li>
              <li><Link to="/activities" onClick={handleClose} tabIndex={drawerOpen ? 0 : -1}>Activities</Link></li>
            </>
          ) : (
            <>
              <li><Link to="/" onClick={handleClose} tabIndex={drawerOpen ? 0 : -1}>Home</Link></li>
              <li><Link to="/login" onClick={handleClose} tabIndex={drawerOpen ? 0 : -1}>Log in</Link></li>
              <li><Link to="/register" onClick={handleClose} tabIndex={drawerOpen ? 0 : -1}>Join the waiting list</Link></li>
            </>
          )}
        </ul>
      </nav>
    </>
  );
}
