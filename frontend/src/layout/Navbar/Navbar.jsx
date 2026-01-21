import React from 'react';
import { useLocation } from 'react-router-dom';
import styles from './Navbar.module.scss';
import Button from '../../components/Button/Button';
import ButtonFrame from '../../components/Button/ButtonFrame';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function Navbar({ onMenuClick }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  const isGamePage = location.pathname === '/game';
  const isActivitiesPage = location.pathname === '/activities';

  return (
    <header className={styles.header}>
      <nav className={styles.navbar} aria-label="Main navigation">

        <div className={styles.leftLinks}>
          <button
            className={styles.menuButton}
            onClick={onMenuClick}
            aria-label="Open menu"
          >
            <div className={styles.menuIcon}>
              <span></span>
              <span></span>
              <span></span>
            </div>
          </button>

          <Link to={isAuthenticated ? '/game' : '/'} aria-label={isAuthenticated ? 'Go to game' : 'Go to home'}>
            <Button
              variant={isAuthenticated && isGamePage ? "secondary" : "primary"}
              className={styles.navLink}
            >
              {isAuthenticated ? 'Game' : 'Home'}
            </Button>
          </Link>
        </div>

        <div className={styles.rightLinks} role="navigation" aria-label="User account">
          {isAuthenticated ? (
            <>
              <div className={styles.link}>
                <Link to="/logout" aria-label="Log out of your account">
                <Button variant="secondary" className={styles.navLink}>
                  Log out
                </Button>
              </Link>
              </div>
              <Link to="/account" aria-label="Go to your account">
                <Button
                  className={styles.navLink}
                  variant="primary"
                >
                  Account
                </Button>
              </Link>
            </>
          ) : (
            <>
              <Link to="/login" aria-label="Log in to your account">
                <Button variant="secondary" className={styles.navLink}>
                  Log in
                </Button>
              </Link>
              <Link to="/register" aria-label="Sign up for an account">
                <Button variant="primary" className={styles.navLink}>
                  Sign up
                </Button>
              </Link>
            </>
          )}
          <div className={styles.account}>
            {/* Reserved for future icons or dropdowns */}
          </div>
        </div>

        <div className={styles.icons} role="navigation" aria-label="Mobile navigation">
          {isAuthenticated ? (
            <>
              {/* <Link to="/menu">Menu</Link> */}
              <Link to="/game" aria-label="Go to game">
                <Button
                  variant={isGamePage ? "primary" : "secondary"}
                  className={styles.navLink}
                >
                  Game
                </Button>
              </Link>
              <Link to="/activities">
                <Button
                  variant={isActivitiesPage ? "primary" : "secondary"}
                  className={styles.navLink}
                >
                  Activities
                </Button>
              </Link>
              <Link to="/account" aria-label="Go to your account">
                <Button variant="secondary" className={styles.navLink}>
                  Account
                </Button>
              </Link>
            </>
          ) : (
            <>
              <Link to="/home" aria-label="Go to home">
                <Button variant="secondary" className={styles.navLink}>
                  Home
                </Button>
              </Link>
              <Link to="/login" aria-label="Log in to your account">
                <Button variant="secondary" className={styles.navLink}>
                  Log in
                </Button>
              </Link>
              <Link to="/register" aria-label="Sign up for an account">
                <Button variant="primary" className={styles.navLink}>
                  Register
                </Button>
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
