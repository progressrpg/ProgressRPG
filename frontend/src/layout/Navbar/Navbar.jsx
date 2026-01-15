import React from 'react';
import styles from './Navbar.module.scss';
import Button from '../../components/Button/Button';
import ButtonFrame from '../../components/Button/ButtonFrame';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function Navbar({ onMenuClick }) {
  const { isAuthenticated } = useAuth();

  return (
    <header className={styles.header}>
      <nav className={styles.navbar}>

        <div className={styles.leftLinks}>
          {/*

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
          */}

          <Link to={isAuthenticated ? '/game' : '/'}>
            <Button variant="primary" className={styles.navLink}>
              {isAuthenticated ? 'Game' : 'Home'}
            </Button>
          </Link>
        </div>

        <div className={styles.rightLinks}>
          {isAuthenticated ? (
            <>
              <div className={styles.link}>
                <Link to="/logout">
                <Button variant="secondary" className={styles.navLink}>
                  Log out
                </Button>
              </Link>
              </div>
              <Link to="/profile">
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
              <Link to="/login">
                <Button variant="secondary" className={styles.navLink}>
                  Log in
                </Button>
              </Link>
              <Link to="/register">
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

        <div className={styles.icons}>
          {isAuthenticated ? (
            <>
              {/* <Link to="/menu">Menu</Link> */}
              <Link to="/game">
                <Button variant="secondary" className={styles.navLink}>
                  Game
                </Button>
              </Link>
              <Link to="/profile">
                <Button variant="secondary" className={styles.navLink}>
                  Account
                </Button>
              </Link>
            </>
          ) : (
            <>
              <Link to="/home">
                <Button variant="secondary" className={styles.navLink}>
                  Home
                </Button>
              </Link>
              <Link to="/login">
                <Button variant="secondary" className={styles.navLink}>
                  Log in
                </Button>
              </Link>
              <Link to="/register">
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
