import React from 'react';
import { useAuth } from '../../context/AuthContext';
import styles from './Footer.module.scss';
import { API_BASE_URL } from '../../config';

export default function Footer() {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) return <p>Loading...</p>;
  const now = new Date();

  return (
    <footer className={styles.footer}>
      {user?.is_staff && isAuthenticated && (
        <a href={`${API_BASE_URL}/admin`} target="_blank" rel="noopener noreferrer">
          Admin Panel
        </a>
      )}
      <p>&copy; {now.getFullYear()} Progress RPG</p>
    </footer>
  );
}
