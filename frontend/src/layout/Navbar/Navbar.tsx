import React, { useEffect, useState } from "react";
import { useLocation, Link } from "react-router";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Popover from "@radix-ui/react-popover";
import * as Accordion from "@radix-ui/react-accordion";
import styles from "./Navbar.module.scss";
import Button from "../../components/Button/Button";
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
  const [mobileAnnouncementsOpen, setMobileAnnouncementsOpen] = useState(false);

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
              <Popover.Root>
                <Popover.Trigger asChild>
                  <Button
                    className={`${styles.navLink} ${styles.announcementsTrigger}`}
                    variant="secondary"
                    ariaLabel="Announcements"
                  >
                    <span aria-hidden="true">🔔</span>
                    {unreadCount > 0 && (
                      <span className={`${styles.unreadBadge} ${styles.unreadBadgeOnTrigger}`}>
                        {unreadCount > 99 ? "99+" : unreadCount}
                      </span>
                    )}
                  </Button>
                </Popover.Trigger>
                <Popover.Portal>
                  <Popover.Content
                    className={styles.announcementsPopoverContent}
                    side="bottom"
                    align="end"
                    sideOffset={6}
                  >
                    <div className={styles.announcementsPopoverHeader}>
                      <strong>Announcements</strong>
                      <button
                        className={styles.popoverActionButton}
                        type="button"
                        onClick={() => {
                          void handleMarkAllRead();
                        }}
                        disabled={unreadCount === 0 || markAllAnnouncementsReadMutation.isPending}
                      >
                        Mark all read
                      </button>
                    </div>

                    {announcementsLoading && (
                      <p className={styles.announcementsEmpty}>Loading announcements...</p>
                    )}

                    {!announcementsLoading && announcements.length === 0 && (
                      <p className={styles.announcementsEmpty}>No announcements yet.</p>
                    )}

                    {!announcementsLoading && announcements.length > 0 && (
                      <Accordion.Root type="multiple" className={styles.announcementsList}>
                        {announcements.map((announcement) => (
                          <Accordion.Item
                            key={announcement.id}
                            className={styles.announcementItem}
                            value={`announcement-${announcement.id}`}
                          >
                            <Accordion.Header>
                              <Accordion.Trigger className={styles.announcementAccordionTrigger}>
                                <div className={styles.announcementTitleRow}>
                                  <span>{announcement.title}</span>
                                  <span className={styles.announcementMetaRight}>
                                    {!announcement.is_read && (
                                      <span className={styles.unreadDot} aria-hidden="true" />
                                    )}
                                  </span>
                                </div>
                                {announcement.summary && (
                                  <p className={styles.announcementSummary}>{announcement.summary}</p>
                                )}
                              </Accordion.Trigger>
                            </Accordion.Header>
                            <Accordion.Content className={styles.announcementAccordionContent}>
                              <p className={styles.announcementBody}>{announcement.body}</p>
                            </Accordion.Content>
                            {!announcement.is_read && (
                              <button
                                className={styles.popoverActionButton}
                                type="button"
                                onClick={() => {
                                  void handleMarkOneRead(announcement.id);
                                }}
                                disabled={markAnnouncementReadMutation.isPending}
                              >
                                Mark read
                              </button>
                            )}
                          </Accordion.Item>
                        ))}
                      </Accordion.Root>
                    )}
                  </Popover.Content>
                </Popover.Portal>
              </Popover.Root>
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
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button
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
                    </button>
                  </DropdownMenu.Trigger>

                  <DropdownMenu.Portal>
                    <DropdownMenu.Content
                      className={styles.accountDropdownContent}
                      align="end"
                      sideOffset={4}
                    >
                      {onHelpClick && (
                        <DropdownMenu.Item
                          className={styles.accountDropdownItem}
                          onSelect={onHelpClick}
                        >
                          <span aria-hidden="true">❓ </span>Tutorial
                        </DropdownMenu.Item>
                      )}
                      {isAnnouncementsEnabled && (
                      <DropdownMenu.Item
                        className={styles.accountDropdownItem}
                        onSelect={(event) => {
                          event.preventDefault();
                          setMobileAnnouncementsOpen((prev) => !prev);
                        }}
                      >
                        <span aria-hidden="true">🔔</span>Announcements
                        {unreadCount > 0 && (
                          <span className={styles.unreadBadge}>
                            {unreadCount > 99 ? "99+" : unreadCount}
                          </span>
                        )}
                      </DropdownMenu.Item>
                      )}
                      {isAnnouncementsEnabled && mobileAnnouncementsOpen && (
                        <div className={styles.mobileAnnouncementsPanel}>
                          <div className={styles.mobileAnnouncementsHeader}>
                            <strong>Announcements</strong>
                            <button
                              className={styles.popoverActionButton}
                              type="button"
                              onClick={() => {
                                void handleMarkAllRead();
                              }}
                              disabled={
                                unreadCount === 0 || markAllAnnouncementsReadMutation.isPending
                              }
                            >
                              Mark all read
                            </button>
                          </div>

                          {announcementsLoading && (
                            <p className={styles.announcementsEmpty}>Loading announcements...</p>
                          )}

                          {!announcementsLoading && announcements.length === 0 && (
                            <p className={styles.announcementsEmpty}>No announcements yet.</p>
                          )}

                          {!announcementsLoading && announcements.length > 0 && (
                            <Accordion.Root type="multiple" className={styles.announcementsList}>
                              {announcements.map((announcement) => (
                                <Accordion.Item
                                  key={announcement.id}
                                  className={styles.announcementItem}
                                  value={`mobile-announcement-${announcement.id}`}
                                >
                                  <Accordion.Header>
                                    <Accordion.Trigger className={styles.announcementAccordionTrigger}>
                                      <div className={styles.announcementTitleRow}>
                                        <span>{announcement.title}</span>
                                        <span className={styles.announcementMetaRight}>
                                          {!announcement.is_read && (
                                            <span className={styles.unreadDot} aria-hidden="true" />
                                          )}
                                        </span>
                                      </div>
                                      {announcement.summary && (
                                        <p className={styles.announcementSummary}>{announcement.summary}</p>
                                      )}
                                    </Accordion.Trigger>
                                  </Accordion.Header>
                                  <Accordion.Content className={styles.announcementAccordionContent}>
                                    <p className={styles.announcementBody}>{announcement.body}</p>
                                  </Accordion.Content>
                                  {!announcement.is_read && (
                                    <button
                                      className={styles.popoverActionButton}
                                      type="button"
                                      onClick={() => {
                                        void handleMarkOneRead(announcement.id);
                                      }}
                                      disabled={markAnnouncementReadMutation.isPending}
                                    >
                                      Mark read
                                    </button>
                                  )}
                                </Accordion.Item>
                              ))}
                            </Accordion.Root>
                          )}
                        </div>
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
