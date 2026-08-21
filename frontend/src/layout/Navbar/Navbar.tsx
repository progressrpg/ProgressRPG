import React, { useEffect } from "react";
import { useLocation, Link } from "react-router";
import DropdownMenu from "../../components/DropdownMenu/DropdownMenu";
import styles from "./Navbar.module.scss";
import Button from "../../components/Button/Button";
import { AnnouncementsBell, MobileAnnouncements } from "./Announcements";
import { useAuth } from "../../context/AuthContext";
import { useGame } from "../../hooks/useGame";
import { useFeatureFlag } from "../../hooks/useFeatureFlag";
import {
  useAnnouncements,
  useMarkAllAnnouncementsRead,
  useMarkAnnouncementRead,
} from "../../hooks/useAnnouncements";

interface NavbarProps {
  onMenuClick?: () => void;
  onHelpClick?: (() => void) | null;
}

export default function Navbar({ onMenuClick, onHelpClick }: NavbarProps) {
  const { isAuthenticated } = useAuth();
  const { announcementUnreadCount, setAnnouncementUnreadCount } = useGame();
  const location = useLocation();
  const isAnnouncementsEnabled = useFeatureFlag("announcements");
  const isMapEnabled = useFeatureFlag("map");

  const { data: announcementsData, isLoading: announcementsLoading } =
    useAnnouncements(isAnnouncementsEnabled);
  const markAnnouncementReadMutation = useMarkAnnouncementRead();
  const markAllAnnouncementsReadMutation = useMarkAllAnnouncementsRead();

  const isTimerPage = location.pathname === "/timer";
  const isHomePage = location.pathname === "/";
  const isLibraryPage = location.pathname.startsWith("/library");
  const isMapPage = location.pathname === "/map";
  const isAccountPage = location.pathname === "/account";

  const announcements = announcementsData?.results ?? [];
  const unreadCount = announcementsData?.unread_count ?? announcementUnreadCount;

  useEffect(() => {
    if (announcementsData) {
      setAnnouncementUnreadCount(announcementsData.unread_count);
    }
  }, [announcementsData, setAnnouncementUnreadCount]);

  const handleMarkOneRead = async (announcementId: number) => {
    const result = await markAnnouncementReadMutation.mutateAsync(announcementId);
    setAnnouncementUnreadCount(result.unread_count);
  };

  const handleMarkAllRead = async () => {
    const result = await markAllAnnouncementsReadMutation.mutateAsync();
    setAnnouncementUnreadCount(result.unread_count);
  };

  const announcementsProps = {
    announcements,
    unreadCount,
    isLoading: announcementsLoading,
    onMarkOneRead: (announcementId: number) => {
      void handleMarkOneRead(announcementId);
    },
    onMarkAllRead: () => {
      void handleMarkAllRead();
    },
    isMarkingOneRead: markAnnouncementReadMutation.isPending,
    isMarkingAllRead: markAllAnnouncementsReadMutation.isPending,
  };

  return (
    <header className={styles.header}>
      <nav className={styles.navbar} aria-label="Main navigation">
        <div className={styles.leftLinks}>
          <Link
            to={isAuthenticated ? "/timer" : "/"}
            aria-label={isAuthenticated ? "Go to timer" : "Go to home"}
          >
            <Button
              variant={isAuthenticated && isTimerPage ? "primary" : "secondary"}
              className={styles.navLink}
            >
              {isAuthenticated ? (
                <>
                  <span aria-hidden="true">⏱ </span>Timer
                </>
              ) : (
                <>
                  <span aria-hidden="true">🏠 </span>Home
                </>
              )}
            </Button>
          </Link>

          {isAuthenticated && (
            <Link to="/library" aria-label="Go to your library">
              <Button
                variant={isLibraryPage ? "primary" : "secondary"}
                className={styles.navLink}
              >
                <span aria-hidden="true">📚 </span>Your library
              </Button>
            </Link>
          )}

          {isAuthenticated && isMapEnabled && (
            <Link to="/map" aria-label="Go to the map">
              <Button
                variant={isMapPage ? "primary" : "secondary"}
                className={styles.navLink}
              >
                <span aria-hidden="true">🗺️ </span>Map
              </Button>
            </Link>
          )}
        </div>

        <div className={styles.rightLinks} role="navigation" aria-label="User account">
          {isAuthenticated ? (
            <>
              {onHelpClick && (
                <Button
                  variant="secondary"
                  className={styles.navLink}
                  onClick={onHelpClick}
                  ariaLabel="Open tutorial"
                >
                  ❓
                </Button>
              )}
              {isAnnouncementsEnabled && (
                <AnnouncementsBell {...announcementsProps} triggerClassName={styles.navLink} />
              )}
              <Link to="/account" aria-label="Go to your account">
                <Button
                  className={styles.navLink}
                  variant={isAccountPage ? "primary" : "secondary"}
                >
                  <span aria-hidden="true">👤 </span>Account
                </Button>
              </Link>

              <Link to="/logout" aria-label="Log out of your account">
                <Button variant="secondary" className={styles.navLink}>
                  <span aria-hidden="true">👋 </span>Log out
                </Button>
              </Link>
            </>
          ) : (
            <>
              <Link to="/login" aria-label="Log in to your account">
                <Button variant="primary" className={styles.navLink}>
                  <span aria-hidden="true">🔑 </span>Log in
                </Button>
              </Link>
            </>
          )}
        </div>

        <div
          className={styles.icons}
          role="navigation"
          aria-label="Mobile navigation"
        >
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
              <Link
                to="/"
                aria-label="Go to home"
                className={`${styles.iconNavButton} ${isHomePage ? styles.iconNavButtonActive : ""}`}
              >
                <svg
                  className={styles.homeIcon}
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path d="M12 3 3 10h2v10h6v-6h2v6h6V10h2L12 3z" />
                </svg>
              </Link>
              <div className={styles.accountMenu}>
                <DropdownMenu.Root align="end" sideOffset={4}>
                  <DropdownMenu.Trigger
                    className={styles.accountTrigger}
                    aria-label="Account menu"
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
                  </DropdownMenu.Trigger>

                  <DropdownMenu.Portal>
                    <DropdownMenu.Content className={styles.accountDropdownContent}>
                      {onHelpClick && (
                        <DropdownMenu.Item
                          className={styles.accountDropdownItem}
                          onSelect={onHelpClick}
                        >
                          <span aria-hidden="true">❓ </span>Tutorial
                        </DropdownMenu.Item>
                      )}
                      {isAnnouncementsEnabled && (
                        <MobileAnnouncements
                          {...announcementsProps}
                          itemClassName={styles.accountDropdownItem}
                        />
                      )}
                      <DropdownMenu.Item className={styles.accountDropdownItem} asChild>
                        <Link to="/account">
                          <span aria-hidden="true">👤 </span>Account
                        </Link>
                      </DropdownMenu.Item>
                      <DropdownMenu.Item className={styles.accountDropdownItem} asChild>
                        <Link to="/logout">
                          <span aria-hidden="true">👋 </span>Log out
                        </Link>
                      </DropdownMenu.Item>
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
              </div>
            </>
          ) : (
            <>
              <Link to="/login" aria-label="Log in to your account">
                <Button variant="primary" className={styles.navLink}>
                  <span aria-hidden="true">🔑 </span>Log in
                </Button>
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
