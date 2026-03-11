import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import styles from './Navbar.module.scss';
import Button from '../../components/Button/Button';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function Navbar({ onMenuClick }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const [accountOpenMobile, setAccountOpenMobile] = useState(false);
  const accountMobileRef = useRef(null);

  const isGamePage = location.pathname === '/game';
  const isVillagePage = location.pathname === '/village';
  const isActivitiesPage = location.pathname === '/activities';
  const isAccountPage = location.pathname === '/account';

  useEffect(() => {
    const handleClickOutside = (event) => {
      const clickInsideMobile = accountMobileRef.current?.contains(event.target);

      if (!clickInsideMobile) {
        setAccountOpenMobile(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className={styles.header}>
      <nav className={styles.navbar} aria-label="Main navigation">

        <div className={styles.leftLinks}>
          <Link to={isAuthenticated ? '/game' : '/'} aria-label={isAuthenticated ? 'Go to game' : 'Go to home'}>
            <Button
              variant={isAuthenticated && isGamePage ? "secondary" : "primary"}
              className={styles.navLink}
            >
              {isAuthenticated ? 'Game' : 'Home'}
            </Button>
          </Link>

          {isAuthenticated && (
            <>
              <Link to="/activities" aria-label="Go to activities">
                <Button
                  variant={isActivitiesPage ? 'secondary' : 'primary'}
                  className={styles.navLink}
                >
                  Activities
                </Button>
              </Link>
              <Link to="/village" aria-label="Go to village">
                <Button
                  variant={isVillagePage ? 'secondary' : 'primary'}
                  className={styles.navLink}
                >
                  Village
                </Button>
              </Link>
            </>
          )}
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
                  variant={isAccountPage ? 'secondary' : 'primary'}
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
          {isAuthenticated ? (
            <>
              <Link to="/game" aria-label="Go to game">
                <Button
                  variant={isGamePage ? "secondary" : "primary"}
                  className={styles.navLink}
                >
                  Game
                </Button>
              </Link>
              <div className={styles.accountMenu} ref={accountMobileRef}>
                <button
                  className={styles.accountTrigger}
                  onClick={() => setAccountOpenMobile((open) => !open)}
                  aria-label="Account menu"
                  aria-haspopup="true"
                  aria-expanded={accountOpenMobile}
                >
                  <svg
                    className={styles.personIcon}
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                    focusable="false"
                  >
                    <circle cx="12" cy="8" r="4" />
                    <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" />
                  </svg>
                </button>
                {accountOpenMobile && (
                  <div className={styles.accountDropdown} role="menu">
                    <Link
                      to="/account"
                      role="menuitem"
                      onClick={() => setAccountOpenMobile(false)}
                    >
                      Account
                    </Link>
                    <Link
                      to="/logout"
                      role="menuitem"
                      onClick={() => setAccountOpenMobile(false)}
                    >
                      Log out
                    </Link>
                  </div>
                )}
              </div>
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
