import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import styles from './Footer.module.scss';
import { API_BASE_URL } from '../../config';

export default function Footer() {
  const { user, isAuthenticated, loading } = useAuth();

  const scrollToTop = () => {
    window.scrollTo({ top: 0, left: 0 });
  };

  if (loading) return <p>Loading...</p>;
  const now = new Date();

  return (
    <footer className={styles.footer}>
      {user?.is_staff && isAuthenticated && (
        <a href={`${API_BASE_URL}/admin`} target="_blank" rel="noopener noreferrer">
          Admin Panel
        </a>
      )}
      <nav className={styles.links} aria-label="Footer links">
        <Link to="/support" onClick={scrollToTop}>Support</Link>
        <Link to="/terms-of-service" onClick={scrollToTop}>Terms of Service</Link>
        <Link to="/privacy-policy" onClick={scrollToTop}>Privacy Policy</Link>
      </nav>
      <p>&copy; {now.getFullYear()} Progress RPG</p>
    </footer>
  );
}
